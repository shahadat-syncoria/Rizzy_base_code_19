# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import requests
import logging
import base64
import re
from odoo import api, models, fields, exceptions, _
from odoo.exceptions import UserError, ValidationError
from ..shopify.utils import parse_gql_nodes

from odoo.http import request
from pprint import pprint

_logger = logging.getLogger(__name__)


class ProductsFetchWizard(models.TransientModel):
    _inherit = 'products.fetch.wizard'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('shopify_keep_fetch_wizard_defaults'):
            return res
        for fname in (
            'date_from',
            'date_to',
            'mappings_only',
            'images_only',
            'feed_only',
            'shopify_product_id',
        ):
            if fname in fields_list:
                res[fname] = False
        return res

    shopify_product_id = fields.Char(string='Shopify product ID')
    mappings_only = fields.Boolean(string='Mappings only', default=False)
    images_only = fields.Boolean(string='Images only', default=False)
    feed_only = fields.Boolean(string='Fetch Feed product only', default=False)

    def fetch_products_to_odoo(self):
        """Build kwargs here so Shopify-specific rules (e.g. stripped product ID) stay in this module."""
        if self.instance_id and self.instance_id.marketplace_instance_type == 'shopify':
            kwargs = {'marketplace_instance_id': self.instance_id}
            product_id_filter = (self.shopify_product_id or '').strip()
            if product_id_filter:
                kwargs['fetch_o_product'] = True
                kwargs['product_id'] = product_id_filter
            if self.mappings_only:
                kwargs['mappings_only'] = True
            return self.shopify_fetch_products_to_odoo(kwargs)
        return super().fetch_products_to_odoo()

    def _cron_fetch_products(self):
        """Cron entrypoint: fetch products for all confirmed Shopify instances."""
        instances = self.env['marketplace.instance'].search([
            ('marketplace_instance_type', '=', 'shopify'),
            ('marketplace_state', '=', 'confirm'),
        ])
        for rec in instances:
            try:
                wizard_id = self.create({'instance_id': rec.id})
                wizard_id.fetch_products()
            except Exception as e:
                self.env['marketplace.logging'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('marketplace.logging'),
                    'create_uid': self.env.user.id,
                    'marketplace_instance_id': rec.id,
                    'level': 'warning',
                    'type': 'client',
                    'summary': 'Shopify cron product fetch failed',
                    'error': str(e).replace('<br>', '').replace('</br>', '\n'),
                })

    def get_product_attribute_id(self, attribute_name):
        attrib_id = self.env['product.attribute'].search(
            [('name', '=', attribute_name)])
        # -------------------------Newly Added---------------------------
        if attribute_name == 'Title' and len(attrib_id) == 0:
            attrib_id = self.env['product.attribute'].sudo().create(
                {
                    'create_variant': 'no_variant',
                    'display_type': 'radio',
                    'name': attribute_name,
                }
            )
        # -------------------------Newly Added---------------------------
        return attrib_id

    def get_product_attribute_value_id(self, attribute_id, product_attribute_id, template_id, attribute_names):
        att_val_id = self.env['product.attribute.value'].search(
            [('attribute_id', 'in', product_attribute_id),
             ('name', 'in', attribute_names),
             ])
        return att_val_id

    def check_for_new_attrs(self, template_id, variant):
        context = dict(self._context or {})
        product_template = self.env['product.template']
        product_attribute_line = self.env['product.template.attribute.line']
        all_values = []
        # attributes = variant.name_value
        attributes = variant

        for attribute in attributes:
            # for attribute_id in eval(attributes):
            attribute_id = attribute.get('name')  # 'Color'
            attribute_names = attribute.get('values')
            product_attribute_id = self.get_product_attribute_id(attribute_id)
            product_attribute_value_id = self.get_product_attribute_value_id(
                attribute_id,
                product_attribute_id.ids,
                template_id,
                attribute_names
            )

            exists = product_attribute_line.search(
                [
                    ('product_tmpl_id', '=', template_id.id),
                    ('attribute_id', 'in', product_attribute_id.ids)
                ]
            )
            if exists:
                pal_id = exists[0]
            else:
                pal_id = product_attribute_line.create(
                    {
                        'product_tmpl_id': template_id.id,
                        'attribute_id': product_attribute_id.id,
                        'value_ids': [[4, product_attribute_value_id]]
                    }
                )

            value_ids = pal_id.value_ids.ids
            for product_attribute_value_id in product_attribute_value_id.ids:
                if product_attribute_value_id not in value_ids:
                    pal_id.write(
                        {'value_ids': [[4, product_attribute_value_id]]})

                    PtAv = self.env['product.template.attribute.value']
                    domain = [
                        ('attribute_id', 'in', product_attribute_id.ids),
                        ('attribute_line_id', '=', pal_id.id),
                        ('product_attribute_value_id',
                         '=', product_attribute_value_id),
                        ('product_tmpl_id', '=', template_id.id)
                    ]

                    attvalue = PtAv.search(domain)

                    if len(attvalue) == 0:
                        product_template_attribute_value_id = PtAv.create({
                            'attribute_id': product_attribute_id.id,
                            'attribute_line_id': pal_id.id,  # attribute_line_id.id,
                            'product_attribute_value_id': product_attribute_value_id,
                            'product_tmpl_id': template_id.id,
                        })

                        all_values.append(
                            product_template_attribute_value_id.id)
        return [(6, 0, all_values)]

    def _shopify_update_attributes(self, odoo_attributes, options, attributes):
        cr = self._cr
        options = [str(i['attribute_id']) for i in options]

        for att in attributes:

            _logger.info("\natt['attribute_code']==>" +
                         str(att['attribute_id']))

            if str(att['attribute_id']) not in odoo_attributes and str(
                    att['attribute_id']) in options:

                # Check Attribureid in database
                print(att['attribute_code'])
                domain = [('name', '=', att['attribute_code'])]
                PA = self.env['product.attribute']
                rec = PA.sudo().search(domain)
                if rec:
                    cr.execute(
                        "select id from product_attribute where id=%s", (rec.id,))
                    rec_id = cr.fetchone()
                else:
                    cr.execute(
                        "insert into product_attribute (name,create_variant,display_type,marketplace_type) "
                        " values(%s, FALSE, 'radio', 'shopify') returning id",
                        (att['attribute_code'],))
                    rec_id = cr.fetchone()
                odoo_attributes[str(att['attribute_id'])] = {
                    'id': rec_id[0],  # id of the attribute in odoo
                    'code': att['attribute_code'],  # label
                    'options': {}
                }

            # attribute values
            if str(att['attribute_id']) in options:
                odoo_att = odoo_attributes[str(att['attribute_id'])]
                for opt in att['options']:
                    if opt != '' and opt != None \
                            and opt not in odoo_att['options']:

                        query = "Select id from product_attribute_value where name='" + opt + "' AND attribute_id='" + \
                                str(odoo_att['id']) + \
                                "' AND marketplace_type='shopify'"
                        cr.execute(query)
                        rec_id = cr.fetchone()

                        if not rec_id:
                            cr.execute(
                                "insert into product_attribute_value (name, attribute_id, marketplace_type)  "
                                "values(%s, %s, 'shopify') returning id",
                                (opt, odoo_att['id']))
                            rec_id = cr.fetchone()

                        # linking id in shopify with id in odoo
                        odoo_att['options'][str(opt)] = rec_id[0]

        return odoo_attributes

    def get_product_data(self):
        catalog_data = []
        products = self.env['product.product'].search([
            ('marketplace_type', '=', 'shopify'),
            ('default_code', '!=', None)
        ])

        if products:
            for product in products:
                product_data = {
                    "sku": product.default_code,
                    "name": product.name,
                    "price": product.list_price,
                    "attribute_set_id": 4,
                    "type_id": "simple"
                }
                catalog_data.append({"product": product_data})
        return catalog_data and [catalog_data, products] or None

    def shopify_fetch_products_to_odoo(self, kwargs):
        kwargs = kwargs or {}
        update_products_no = 0
        sp_product_list = []
        existing_ids = []
        cr = self._cr
        # fetching products already fetched from shopify to skip those already created
        # cr.execute("select shopify_id from product_template "
        #            "where shopify_id is not null ")
        # products = cr.fetchall()
        # ids = [str(i[0]) for i in products] if products else []
        #
        # cr.execute("select shopify_id from product_product "
        #            "where shopify_id is not null")
        # products = cr.fetchall()
        # for i in products:
        #     ids.append(i[0]) if i[0] not in ids else None

        categ_list = []

        marketplace_instance_id = kwargs.get('marketplace_instance_id')
        if marketplace_instance_id:
            _logger.info(
                "Shopify fetch products (GraphQL): instance=%s single_product=%s date_from=%s date_to=%s",
                marketplace_instance_id.id,
                bool(kwargs.get('fetch_o_product')),
                self.date_from,
                self.date_to,
            )

            headers = {'X-Service-Key': marketplace_instance_id.token}

            use_graphql = getattr(marketplace_instance_id, "use_graphql", False)
            products = []

            if not use_graphql:
                raise exceptions.UserError(
                    _("This fetch is GraphQL-only. Enable 'Use GraphQL' on the Shopify instance.")
                )

            def _money_to_str(m):
                if m is None:
                    return None
                if isinstance(m, dict):
                    return str(m.get("amount"))
                return str(m)

            def _normalize_product_node(product_node):
                product_id = product_node.get("id")
                product_id_numeric = product_node.get("id").split("/")[-1] if product_id else None

                # REST-like options shape used by shopify.feed.products import
                gql_options = product_node.get("options") or []
                options_list = []
                for idx, opt in enumerate(gql_options, start=1):
                    options_list.append(
                        {
                            "id": idx,
                            "position": idx,
                            "name": opt.get("name"),
                            "values": opt.get("values") or [],
                        }
                    )

                # Variants normalization
                variants_nodes = ((product_node.get("variants") or {}).get("nodes")) or []
                normalized_variants = []
                selected_by_name = {}
                for v in variants_nodes:
                    selected_by_name = {so.get("name"): so.get("value") for so in v.get("selectedOptions") or []}
                    variant = {
                        "id": v.get("id").split("/")[-1] if v.get("id") else None,
                        "sku": v.get("sku"),
                        "price": _money_to_str(v.get("price")),
                        "compare_at_price": _money_to_str(v.get("compareAtPrice")),
                        "inventory_policy": str(v.get("inventoryPolicy") or "").lower() or None,
                        "taxable": v.get("taxable"),
                        "barcode": v.get("barcode"),
                        "image_id": v.get("image", {}).get("id", "").split("/")[-1] if v.get("image") and v.get("image", {}).get("id") else None,
                        "inventory_item_id": v.get("inventoryItem", {}).get("id", "").split("/")[-1] if v.get("inventoryItem") and v.get("inventoryItem", {}).get("id") else None,
                        "product_id": product_id_numeric,
                        # 2025-01 Admin GraphQL: these fields are not on ProductVariant anymore.
                        "fulfillment_service": None,
                        "inventory_management": None,
                        "requires_shipping": None,
                        "weight": None,
                    }
                    # REST-like option1/option2/option3 fields
                    for idx, opt in enumerate(options_list[:3], start=1):
                        opt_name = opt.get("name")
                        if opt_name and selected_by_name.get(opt_name) not in [None, ""]:
                            variant[f"option{idx}"] = selected_by_name.get(opt_name)
                    normalized_variants.append(variant)

                # Images normalization (variant_ids not available via this query; keep empty)
                images_nodes = ((product_node.get("images") or {}).get("nodes")) or []
                normalized_images = []
                main_image_src = None
                for img in images_nodes:
                    normalized_images.append(
                        {
                            "id": img.get("id").split("/")[-1] if img.get("id") else None,
                            "product_id": product_id_numeric,
                            "src": img.get("originalSrc"),
                            "variant_ids": [],
                        }
                    )
                    if not main_image_src and img.get("originalSrc"):
                        # Pick the first image as the main image (position is not available on Image in 2025-01).
                        main_image_src = img.get("originalSrc")
                if not main_image_src and normalized_images:
                    main_image_src = normalized_images[0].get("src")

                status = (product_node.get("status") or "").lower()
                tags = product_node.get("tags") or []
                tags_str = ",".join(tags) if isinstance(tags, list) else str(tags)

                return {
                    "id": product_id_numeric,
                    "title": product_node.get("title"),
                    "body_html": product_node.get("bodyHtml"),
                    "vendor": product_node.get("vendor"),
                    "product_type": product_node.get("productType"),
                    "status": status,
                    "tags": tags_str,
                    "created_at": product_node.get("createdAt"),
                    "updated_at": product_node.get("updatedAt"),
                    "published_at": product_node.get("publishedAt"),
                    "options": options_list,
                    "variants": normalized_variants,
                    "image": {"src": main_image_src} if main_image_src else None,
                    "images": normalized_images,
                }

            if use_graphql:
                # Day 3: GraphQL cursor pagination (edges/node -> REST-like structure)
                if kwargs.get('fetch_o_product'):
                    product_id = (str(kwargs.get('product_id') or self.shopify_product_id or "")).strip()
                    if not product_id:
                        raise exceptions.UserError(
                            _("Please set a Shopify product ID to fetch a single product.")
                        )
                    query_by_id = """
                    query SyncoriaProductById($id: ID!) {
                      product(id: $id) {
                        id
                        title
                        bodyHtml
                        vendor
                        productType
                        status
                        tags
                        createdAt
                        updatedAt
                        publishedAt
                        options { name values }
                        variants(first: 250) {
                          nodes {
                            id
                            sku
                            price
                            compareAtPrice
                            taxable
                            inventoryPolicy
                            barcode
                            selectedOptions { name value }
                            inventoryItem { id }
                            image { id }
                          }
                        }
                        images(first: 250) {
                          nodes {
                            id
                            originalSrc
                          }
                        }
                      }
                    }
                    """
                    res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers=headers,
                        url='/graphql.json',
                        query=query_by_id,
                        variables={"id": f"gid://shopify/Product/{product_id}"},
                        type="POST",
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if res.get("errors"):
                        raise exceptions.UserError(_("Error Occurred %s") % res.get("errors"))
                    node = (res.get("data") or {}).get("product") or {}
                    products = [_normalize_product_node(node)] if node else []
                else:
                    query_filter = ""
                    if self.date_from and not self.date_to:
                        query_filter = "created_at:>=%s" % self.date_from.strftime("%Y-%m-%d")
                    if not self.date_from and self.date_to:
                        query_filter = "created_at:<=%s" % self.date_to.strftime("%Y-%m-%d")
                    if self.date_from and self.date_to:
                        query_filter = "created_at:>=%s created_at:<=%s" % (
                            self.date_from.strftime("%Y-%m-%d"),
                            self.date_to.strftime("%Y-%m-%d"),
                        )

                    products_connection_query = """
                    query SyncoriaProducts($first: Int!, $after: String, $query: String) {
                      products(first: $first, after: $after, query: $query) {
                        edges {
                          node {
                            id
                            title
                            bodyHtml
                            vendor
                            productType
                            status
                            tags
                            createdAt
                            updatedAt
                            publishedAt
                            options { name values }
                            variants(first: 250) {
                              nodes {
                                id
                                sku
                                price
                                compareAtPrice
                                taxable
                                inventoryPolicy
                                barcode
                                selectedOptions { name value }
                                inventoryItem { id }
                                image { id }
                              }
                            }
                            images(first: 250) {
                              nodes {
                                id
                                originalSrc
                              }
                            }
                          }
                        }
                        pageInfo { hasNextPage endCursor }
                      }
                    }
                    """
                    after = None
                    while True:
                        variables = {"first": 250, "after": after, "query": query_filter or None}
                        res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                            headers=headers,
                            url='/graphql.json',
                            query=products_connection_query,
                            variables=variables,
                            type="POST",
                            marketplace_instance_id=marketplace_instance_id,
                        )
                        if res.get("errors"):
                            raise exceptions.UserError(_("Error Occurred %s") % res.get("errors"))
                        connection = (res.get("data") or {}).get("products") or {}
                        for node in parse_gql_nodes(connection):
                            products.append(_normalize_product_node(node))

                        page_info = connection.get("pageInfo") or {}
                        if not page_info.get("hasNextPage"):
                            break
                        after = page_info.get("endCursor")

                _logger.info("Product fetch (GraphQL) done: %s", len(products))
            # REST path intentionally removed (GraphQL-only).
            # if not kwargs.get('fetch_o_product', False):
            #     updated_products = []
            #     update_url = '/products.json'
            #     if self.date_from and not self.date_to:
            #         update_url += '?updated_at_min=%s' % self.date_from.strftime(
            #             "%Y-%m-%dT00:00:00" + tz_offset)
            #     if not self.date_from and self.date_to:
            #         update_url += '?updated_at_max=%s' % self.date_to.strftime(
            #             "%Y-%m-%dT23:59:59" + tz_offset)
            #     if self.date_from and self.date_to:
            #         update_url += '?updated_at_min=%s' % self.date_from.strftime(
            #             "%Y-%m-%dT00:00:00" + tz_offset)
            #         update_url += '&updated_at_max=%s' % self.date_to.strftime(
            #             "%Y-%m-%dT23:59:59" + tz_offset)
            #     while True:
            #         fetched_products, next_link = self.env[
            #             'marketplace.connector'].shopify_api_call(
            #             headers=headers,
            #             url=update_url,
            #             type=type_req,
            #             marketplace_instance_id=marketplace_instance_id,
            #             params=params
            #         )
            #         try:
            #             if 'errors' in fetched_products and len(fetched_products['errors']) > 0:
            #                 raise UserError('Something is wrong. Please make sure the store is configured correctly.')
            #             if type(fetched_products).__name__ == 'list':
            #                 updated_products += fetched_products['products']
            #             elif type(fetched_products).__name__ == 'dict':
            #                 updated_products += fetched_products.get('products') or [fetched_products.get('product')]
            #             else:
            #                 updated_products += [fetched_products['product']]
            #
            #             if next_link:
            #                 if next_link.get("next"):
            #                     full_url = next_link.get("next").get("url")
            #                     """
            #                         The pagination url contains the full url so we have to split the string
            #                     """
            #                     full_url_arr_split = full_url.split('/')
            #                     url = '/' + full_url_arr_split[-1]
            #                     if 'limit' in params:
            #                         del params['limit']
            #                 else:
            #                     break
            #             else:
            #                 break
            #         except Exception as e:
            #             _logger.info("Exception occurred: %s", e)
            #             raise exceptions.UserError(_("Error Occurred %s") % e)
            #
            #     created_product_id = [prod.get('id') for prod in products]
            #     for prod in updated_products:
            #         if prod['id'] not in created_product_id:
            #             products += [prod]
            if type(products).__name__ == 'list':
                configurable_products = {"products": products}
            else:
                configurable_products = fetched_products


            # Update Product Categories
            # in shopify, each product can have one product type(category), so we are fetching all the product types
            # from shopify
            # and creating those in odoo. For the products updated from shopify,
            # we will be showing all the shopify categories in a separate field
            try:
                if kwargs.get('mappings_only'):
                    for product in configurable_products['products']:
                        for variant in product['variants']:
                            product_id = False
                            mapping_id = self.env['shopify.product.mappings'].search(
                                [('shopify_id', '=', variant['id']),
                                 ('shopify_instance_id', '=', marketplace_instance_id.id)])
                            if mapping_id and mapping_id.product_id:
                                # product_id = self.env['product.product'].search([('default_code', '=', variant['sku'])], limit=1)
                                product_id = mapping_id.product_id
                            # if marketplace_instance_id.is_sku and not product_id:
                            #     product_id = self.env['product.product'].search([('default_code', '=', variant['sku'])], limit=1)
                            if not product_id:
                                if marketplace_instance_id.product_mapping == 'sku':
                                    product_id = self.env['product.product'].search(
                                        [('default_code', '=', variant['sku'])], limit=1)
                                elif marketplace_instance_id.product_mapping == 'barcode':
                                    product_id = self.env['product.product'].search(
                                        [('barcode', '=', variant['barcode'])], limit=1)

                            if product_id:
                                vals = {
                                    'product_id': product_id.id,
                                    'shopify_instance_id': marketplace_instance_id.id,
                                    'name': variant['sku'],
                                    'shopify_id': variant['id'],
                                    'shopify_parent_id': variant['product_id'],
                                    'shopify_inventory_id': variant['inventory_item_id']
                                }
                                mapping_id = self.env['shopify.product.mappings'].search([('shopify_id', '=', variant['id']), ('shopify_instance_id', '=', marketplace_instance_id.id)])
                                if not mapping_id:
                                    self.env['shopify.product.mappings'].create(vals)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                if self.images_only:
                    for product in configurable_products['products']:
                        for image in product['images']:
                            self.env['shopify.image.queue'].create({
                                'shopify_instance_id': marketplace_instance_id.id,
                                'shopify_image_id': str(image['id']),
                                'product_id': str(image['product_id']),
                                'position': image.get('position') or 0,
                                'src': image['src'],
                                'variant_ids': json.dumps(image['variant_ids'])
                            })
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'reload',
                    }
                if configurable_products.get('errors'):
                    errors = configurable_products.get('errors')
                    _logger.warning("Exception occured: {}".format(errors))
                    raise exceptions.UserError(_("Error Occured {}".format(errors)))
                if configurable_products.get('products'):
                    product_list = configurable_products.get('products')
                else:
                    product_list = [configurable_products.get('product')] if type(configurable_products.get('products')) != list else configurable_products.get('products')

                all_feed_products_rec = [self.create_feed_parent_product(product,marketplace_instance_id) for product in product_list]
                if not self.feed_only:
                    for process_product in all_feed_products_rec:
                        update_products_no += 1
                        process_product.process_feed_product()
                        process_product.write({"state":'processed'})

            except Exception as e:
                _logger.warning("Exception occured: {}".format(e.args))
                raise exceptions.UserError(_("Error Occured %s") % e)

        _logger.info("%d products are successfully updated." % update_products_no)

        if kwargs.get('fetch_o_product'):
            """Return the Product ID"""
            return sp_product_list

    def update_sync_history(self, vals):
        from datetime import datetime
        SycnHis = self.env['marketplace.sync.history'].sudo()
        synhistory = SycnHis.search(
            [('marketplace_type', '=', 'shopify')], limit=1)
        if not synhistory:
            synhistory = SycnHis.search(
                [('marketplace_type', '=', 0)], limit=1)
            synhistory.write({'marketplace_type': 'shopify'})
        vals['last_product_sync'] = datetime.now()
        synhistory.write(vals)

    def shopify_fetch_products_from_odoo(self):
        url = '/rest/V1/products'
        type = 'POST'
        headers = {
            'Content-Type': 'application/json'
        }
        product_data = self.get_product_data()

        if not product_data:
            return
        updated_list = {}
        for product in product_data[0]:
            try:
                product_list,next_link = self.env[
                    'marketplace.connector'].shopify_api_call(
                    headers=headers,
                    url=url,
                    type=type,
                    data=product
                )
                if product_list.get('sku'):
                    updated_list[product_list['sku']] = product_list.get(
                        'id')
            except:
                pass
        if updated_list:
            for product in product_data[1]:
                if product.default_code in updated_list:
                    product.write({
                        'marketplace_type': 'shopify',
                        'shopify_id': str(
                            updated_list[product.default_code])
                    })
                    product.product_tmpl_id.write({
                        'marketplace_type': 'shopify',
                        'shopify_id': str(
                            updated_list[product.default_code])
                    })
        _logger.info("%s product(s) updated", len(updated_list))
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def shopify_image_processing(self, image_url):
        if image_url:
            image = False
            # shopify_host = self.env['ir.config_parameter'].sudo().get_param('odoo11_shopify2.shopify_host')
            # image_url = 'http://' + shopify_host + '/pub/media/catalog/product' + file
            if requests.get(image_url).status_code == 200:
                image = base64.b64encode(
                    requests.get(image_url).content)
            return image
        else:
            return False

    def get_comb_indices(self, options):
        comb_indices = ''
        i = 1
        for value in [option.get('values') for option in options]:
            for cmb in value:
                if cmb not in comb_indices:
                    comb_indices += ',' + cmb if i != 1 else cmb
            i = 0 if i == 1 else 0
        print(comb_indices)
        return comb_indices
        # prints
        # Default Title,Red,Blue


    def create_feed_parent_product(self, product, instance_id):
        try:
            domain = [('parent', '=', True)]
            domain += [('shopify_id', '=', product['id'])]
            fp_product = self.env['shopify.feed.products'].sudo().search(domain, limit=1)
            if not fp_product:
                record = self.env['shopify.feed.products'].sudo().create({
                    'instance_id': self.instance_id.id if self.instance_id else instance_id.id,
                    'parent': True,
                    'title': product['title'],
                    'shopify_id': product['id'],
                    'inventory_id': product.get('inventory_item_id'),
                    'product_data': json.dumps(product),
                })
                record.env.cr.commit()
                _logger.info("Shopify Feed Parent Product Created-{}".format(record))
                return record
            else:
                fp_product.write({
                    'product_data': json.dumps(product),
                    'inventory_id': product.get('inventory_item_id')
                })
                return fp_product
        except Exception as e:
            _logger.warning("Exception-{}".format(e.args))

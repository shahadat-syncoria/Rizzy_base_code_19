# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import re
import datetime
from odoo.exceptions import AccessError, UserError
from ..shopify.utils import *
from odoo import models, api, fields, tools, exceptions, _

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_product = fields.Boolean(string='Is Shopify Product', copy=False, default=False)
    # shopify_id = fields.Char(string="Shopify Id", store=True, copy=False)
    shopify_image_id = fields.Char(
        string="Shopify Image Id", store=True, copy=False)
    shopify_inventory_id = fields.Char(
        string="Shopify Inventory Id", store=True, copy=False)
    shopify_categ_ids = fields.One2many('shopify.product.category',
                                        'product_tmpl_id',
                                        string="Shopify Categories")
    shopify_type = fields.Char(string="Shopify Product Type",
                               readonly=True, store=True)
    custom_option = fields.Boolean(string="Custom Option", default=False)
    # New Fields
    shopify_published_scope = fields.Char()
    shopify_tags = fields.Char()
    shopify_template_suffix = fields.Char()
    shopify_variants = fields.Char()
    shopify_vendor = fields.Char()
    # Fields for Shopify Products
    shopify_compare_price = fields.Monetary(string='Compare at price',
                                            help="To display a markdown, enter a value higher than your price")
    shopify_charge_tax = fields.Boolean(string='Charge tax?')
    # shopify_track_qty = fields.Boolean(string='Track quantity?')
    shopify_product_status = fields.Selection(
        string='Product status',
        selection=[('draft', 'Draft'), ('active', 'Active'),
                   ('archived', 'Archived')],
        default='active',
    )
    shopify_collections = fields.Char()
    # shopify_collection_ids = fields.Many2many(
    #     string='Shopify Collection',
    #     comodel_name='shopify.product.collectoon',
    #     relation='shopfy_product_collectoon_product_template_rel',
    #     column1='shopfy_product_collectoon_id',
    #     column2='product_template_id',
    # )
    shopify_origin_country_id = fields.Many2one(
        string='Shopify Country Code of Origin',
        comodel_name='res.country',
        ondelete='restrict',
    )
    shopify_province_origin_id = fields.Many2one(
        string='Shopify Province Code of Origin',
        comodel_name='res.country.state',
        ondelete='restrict',
    )
    # Currency Conversion
    shopify_currency_id = fields.Many2one(
        string='Shopify Currency',
        comodel_name='res.currency',
        ondelete='restrict',
    )
    shopify_price = fields.Float()
    shopify_update_variants = fields.Boolean()
    shopify_show_on_hand_qty_status_button = fields.Boolean(
        compute='_shopify_compute_show_qty_status_button')
    shopify_show_forecasted_qty_status_button = fields.Boolean(
        compute='_shopify_compute_show_qty_status_button')



    def _shopify_compute_show_qty_status_button(self):
        for template in self:
            template.shopify_show_on_hand_qty_status_button = template.type == 'product'
            template.shopify_show_forecasted_qty_status_button = template.type == 'product'

    shopify_qty_available = fields.Float(
        'Shopify Qty On Hand', compute='_compute_shopify_quantities',
        compute_sudo=False, digits='Product Unit of Measure')

    def _compute_shopify_quantities(self):
        res = self._compute_shopify_quantities_dict()
        for template in self:
            template.shopify_qty_available = res[template.id]['shopify_qty_available']

    def _compute_shopify_quantities_dict(self):
        variants_available = {
            p['id']: p for p in self.product_variant_ids.read(['shopify_qty_available'])
        }
        prod_available = {}
        for template in self:
            shopify_qty_available = 0
            for p in template.product_variant_ids:
                shopify_qty_available += variants_available[p.id]["shopify_qty_available"]
            prod_available[template.id] = {
                "shopify_qty_available": shopify_qty_available,
            }
        return prod_available

    # Be aware that the exact same function exists in product.product
    def shopify_action_open_quants(self):
        return self.product_variant_ids.filtered(
            lambda p: p.active or p.qty_available != 0).shopify_action_open_quants()

    @api.onchange('shopify_origin_country_id')
    def _onchange_shopify_origin_country_id1(self):
        state_ids = self.env['res.country.state'].search(
            [('country_id', '=', self.shopify_origin_country_id.id)]).ids
        res = {'domain': {'shopify_province_origin_id': [
            ('id', 'in', state_ids)]}}
        return res

    @api.onchange('shopify_origin_country_id')
    def _onchange_shopify_origin_country_id2(self):
        for rec in self:
            variants = rec.product_variant_id + rec.product_variant_ids
            for variant in variants:
                variant.shopify_origin_country_id = rec.shopify_origin_country_id.id

    @api.onchange('shopify_province_origin_id')
    def _onchange_shopify_province_origin_id(self):
        for rec in self:
            variants = rec.product_variant_id + rec.product_variant_ids
            for variant in variants:
                variant.shopify_province_origin_id = rec.shopify_province_origin_id.id

    def compute_shopify_price(self,marketplace_instance_id):
        for rec in self:
            if marketplace_instance_id:
                # marketplace_instance_id = marketplace_instance_id
                rec.shopify_currency_id = marketplace_instance_id.pricelist_id.currency_id.id
                if marketplace_instance_id:
                    for variant in rec.product_variant_ids:
                        variant_line = marketplace_instance_id.pricelist_id.item_ids.filtered(lambda l: l.product_id.id == variant.id)
                        template_line = marketplace_instance_id.pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id.id == rec.id)
                        item_line = variant_line or template_line
                        if item_line:
                            rec.shopify_price = item_line.fixed_price
                            rec.message_post(body="Shopify Product Price updated for Product-{} with price-{}".format(rec.name, item_line.fixed_price))
            else:
                msg = "Shopify Instance ID missing for {}".format(rec)
                _logger.warning(msg)
                # rec.message_post(body=msg)

    def create_image_attachment(self):
        self.ensure_one()
        IrParamSudo = self.env['ir.config_parameter'].sudo()
        web_base_url = IrParamSudo.get_param('web.base.url')
        images = []
        attachment_ids_to_delete = []
        variant_images = {}
        if self.image_1920:
            attachment = self.env['ir.attachment'].create({
                'name': self.name + '_image_1920',
                'datas': self.image_1920,
                'public': True,
            })
            src_url = web_base_url + '/web/content/' + str(attachment.id)
            images.append(src_url)
            attachment_ids_to_delete.append(attachment.id)
        for images_extra in self.product_template_image_ids:
            attachment_extra = self.env['ir.attachment'].create({
                'name': self.name + '_image_1920',
                'datas': images_extra.image_1920,
                'public': True,
            })
            src_url_extra = web_base_url + '/web/image/' + str(attachment_extra.id)
            images.append(src_url_extra)
            attachment_ids_to_delete.append(attachment_extra.id)
        if len(self.product_variant_ids) > 1:
            for variant in self.product_variant_ids.filtered(lambda p: p.image_1920):
                attachment_variant = self.env['ir.attachment'].create({
                    'name': self.name + '_image_1920',
                    'datas': variant.image_1920,
                    'public': True,
                })
                src_url_variant = web_base_url + '/web/image/' + str(attachment_variant.id)
                variant_images[variant.id] = src_url_variant
                attachment_ids_to_delete.append(attachment_variant.id)
        return images, attachment_ids_to_delete, variant_images

    def action_create_shopify_product(self, instance):
        mapping = self.env['shopify.product.mappings'].search([('product_tmpl_id', '=', self.id), ('shopify_instance_id', '=', instance.id)], limit=1)
        data = get_protmpl_vals(self, 'create', mapping, instance)
        shopify_pt_request(self, data, 'create', mapping, instance)
        self.shopify_product = True

    def action_update_shopify_product(self, instance):
        mapping = self.env['shopify.product.mappings'].search([('product_tmpl_id', '=', self.id), ('shopify_instance_id', '=', instance.id)], limit=1)
        if not mapping:
            return
        data = get_protmpl_vals(self, 'update', mapping, instance)
        shopify_pt_request(self, data, 'update', mapping, instance)
        # if self.product_variant_ids:
        #     for variant in self.product_variant_ids:
        #         variant.action_update_inventory_item()

    def action_update_odoo_cost_product(self):
        for rec in self:
            for variant in rec.product_variant_ids.filtered(lambda p: p.shopify_inventory_id):
                variant.action_update_odoo_cost_product()

    def action_update_shopify_cost_product(self, marketplace_instance_id):
        for rec in self:
            for variant in rec.product_variant_ids:
                variant.action_update_shopify_cost_product(marketplace_instance_id)

    def action_fetch_shopify_product_to_odoo(self):
        try:
            if self.shopify_id and self.shopify_instance_id:
                marketplace_instance_id = self.shopify_instance_id
                if getattr(marketplace_instance_id, "use_graphql", False):
                    query = """
                    query SyncoriaProductForMapping($id: ID!) {
                      product(id: $id) {
                        id
                        options { name position values }
                        variants(first: 250) {
                          nodes {
                            legacyResourceId
                            inventoryItem { legacyResourceId }
                            image { legacyResourceId }
                            selectedOptions { name value }
                          }
                        }
                      }
                    }
                    """
                    res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=query,
                        variables={"id": to_shopify_gid("Product", self.shopify_id)},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if res.get("errors"):
                        raise UserError(_("Error: %s") % res.get("errors"))
                    p = ((res.get("data") or {}).get("product") or {})
                    variants_nodes = (((p.get("variants") or {}).get("nodes")) or [])
                    options = p.get("options") or []
                    response = {
                        "product": {
                            "variants": [
                                {
                                    "id": int(v.get("legacyResourceId") or 0) if v.get("legacyResourceId") else None,
                                    "inventory_item_id": int(((v.get("inventoryItem") or {}).get("legacyResourceId") or 0)) if (v.get("inventoryItem") or {}).get("legacyResourceId") else None,
                                    "image_id": int(((v.get("image") or {}).get("legacyResourceId") or 0)) if (v.get("image") or {}).get("legacyResourceId") else None,
                                    "selectedOptions": v.get("selectedOptions") or [],
                                } for v in variants_nodes
                            ],
                            "options": options,
                        }
                    }
                    class _Fake:
                        status_code = 200
                        def json(self_inner):
                            return response
                    res = _Fake()
                else:
                    raise UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
                shopify_var_ids = self.env['product.product']
                if res.status_code == 200:
                    response = res.json()
                    if len(response.get('product', {}).get("variants")) > 1:
                        variants = response.get('product', {}).get("variants")
                        options = response.get('product', {}).get("options")
                        options_dict = {}
                        for opt in options:
                            if opt:
                                options_dict['option' +
                                             str(opt['position'])] = opt['name']

                        for var in variants:
                            if var.get("selectedOptions"):
                                # GraphQL response path: map selectedOptions back into option1/2/3 using `options_dict`.
                                selected = {so.get("name"): so.get("value") for so in (var.get("selectedOptions") or [])}
                                for pos_key, opt_name in options_dict.items():
                                    idx = int(pos_key.replace("option", "") or 0)
                                    if 1 <= idx <= 3 and opt_name in selected:
                                        var[pos_key] = selected.get(opt_name)
                            fields = list([key for key, value in var.items()])
                            pro_domain = []
                            ptav_ids = []
                            for key, value in options_dict.items():
                                if key in fields:
                                    attribute_id = self.env['product.attribute'].sudo().search(
                                        [('name', '=', value)], limit=1).id
                                    domain = [('attribute_id', '=', attribute_id)]
                                    domain += [('name', '=', var[key]), ('product_tmpl_id', '=', self.id)]
                                    ptav = self.env['product.template.attribute.value'].sudo().search(
                                        domain, limit=1)
                                    ptav_ids += ptav.ids

                            pro_domain += [('product_tmpl_id', '=', self.id)]
                            if len(ptav_ids) > 1:
                                for ptav_id in ptav_ids:
                                    pro_domain += [('product_template_attribute_value_ids', '=', ptav_id)]
                            elif len(ptav_ids) == 1:
                                pro_domain += [('product_template_attribute_value_ids', 'in', ptav_ids)]

                            var_id = self.env['product.product'].sudo().search(pro_domain, limit=1)
                            _logger.info("var_id-->%s", var_id)

                            if var_id:
                                shopify_var_ids += var_id
                                var_id.write({
                                    'shopify_instance_id': self.shopify_instance_id.id,
                                    'shopify_id': str(var.get('id') or ''),
                                    'shopify_inventory_id': str(var.get('inventory_item_id') or ''),
                                    'shopify_image_id': str(var.get('image_id') or ''),
                                })
                                var_id.env.cr.commit()

                    if shopify_var_ids:
                        empty_shopify_ids = self.product_variant_ids - shopify_var_ids
                        for variant_id in empty_shopify_ids:
                            variant_id.write({
                                'shopify_instance_id': False,
                                'shopify_id': False,
                                'shopify_inventory_id': False,
                                'shopify_image_id': False,
                            })
                            variant_id.env.cr.commit()

                else:
                    raise UserError(_("Error: {}".format(res.text)))


        except Exception as e:
            _logger.info("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured 5 %s") % e)

    def server_action_shopify_create_update_product(self):
        for record in self:
            if record.marketplace_type == 'shopify':
                if record.shopify_id:
                    record.action_update_shopify_product()
                else:
                    record.action_create_shopify_product()
            else:
                raise UserError(
                    _("Marketplace type is not set for Shopify(Product: %s)") % record.name)

    def server_action_shopify_update_stock(self):
        Connector = self.env['marketplace.connector']
        marketplace_instance_id = self.shopify_instance_id
        products = self._shopify_get_product_list(self.ids)

        for item in products:
            try:
                if getattr(marketplace_instance_id, "use_graphql", False):
                    query = """
                    query SyncoriaInventoryLevels($id: ID!) {
                      inventoryItem(id: $id) {
                        inventoryLevels(first: 250) {
                          nodes {
                            location { id }
                            quantities(names: ["available"]) {
                              name
                              quantity
                            }
                          }
                        }
                      }
                    }
                    """
                    stock_item, _next = Connector.shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=query,
                        variables={"id": to_shopify_gid("InventoryItem", item.shopify_inventory_id)},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if stock_item.get('errors'):
                        continue
                    nodes = ((((stock_item.get('data') or {}).get('inventoryItem') or {}).get('inventoryLevels') or {}).get('nodes') or [])
                    for node in nodes:
                        qty = 0
                        for q in node.get("quantities") or []:
                            if q.get("name") == "available":
                                qty = int(q.get("quantity") or 0)
                                break
                        self.change_product_qty({
                            "location_id": ((node.get("location") or {}).get("id") or "").split("/")[-1],
                            "available": qty,
                        }, item)
                else:
                    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))

            except Exception as e:
                _logger.warning("Exception-%s", e.args)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def _shopify_get_product_list(self, active_ids):
        if self._context.get('active_model') == 'product.product':
            products = self.env['product.product'].search([
                ('marketplace_type', '=', 'shopify'),
                ('id', 'in', active_ids)
            ])
        if self._context.get('active_model') == 'product.template':
            # Cannot find products
            products = self.env['product.product'].search([
                ('marketplace_type', '=', 'shopify'),
                ('product_tmpl_id', 'in', active_ids)
            ])
        return products

    def change_product_qty(self, stock_info, product_info):
        warehouse = self.env['stock.warehouse'].search([("shopify_warehouse_id", "=", stock_info.get(
            "location_id")), ("shopify_warehouse_active", "=", True)], limit=1)
        # Before creating a new quant, the quand `create` method will check if
        # it exists already. If it does, it'll edit its `inventory_quantity`
        # instead of create a new one.
        if warehouse:
            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_info.id,
                'location_id': warehouse.lot_stock_id.id,
                'inventory_quantity': stock_info.get('available'),
            }).action_apply_inventory()

    def action_update_shopify_options(self):
        odoo_variants_to_update = []
        odoo_variants_to_remove = []
        odoo_variants_to_remove_str = []
        excluded_attribute_ids = []
        product_data = self.get_shopify_product_data()
        if product_data:
            shopify_missing_options = {}
            attribute_line_list = {}
            for ptal in self.attribute_line_ids:
                valid_value_ids = ptal.value_ids - ptal.shopify_value_ids
                attribute_line_list.update(
                    {ptal.attribute_id.name: valid_value_ids.mapped('name')})
                excluded_attribute_ids += ptal.shopify_value_ids.ids

            # ===================================================================
            # Added Date: 26/08/2022
            # Requirement from Ariful Haque: Remove Excluded Variants Shopify Information
            # Responsible: Jahintaqi Chisty
            # TO DO: Removed Shopify Excluded Values Variants Information
            # >>>>>>>>>>>>>>>>>>>>> Remove Excluded Variants Shopify Information <<<<<<<<<<<<<<<<<<<

            product_product = self.env['product.product'].search(
                [("product_template_variant_value_ids.product_attribute_value_id", "in", excluded_attribute_ids),
                 ("product_tmpl_id", "=", self.id)])
            product_product.shopify_id = None
            product_product.shopify_inventory_id = None
            product_product.shopify_image_id = None

            _logger.info("attribute_line_list ===>>>{}".format(
                attribute_line_list))

            if product_data.get('product', {}).get('options'):
                options = product_data.get('product', {}).get('options') or []
                for option in options:
                    _logger.info("{}===>>>{}".format(
                        option['name'], option['values']))
                    if attribute_line_list.get(option['name']):
                        missing_values = list(set(attribute_line_list.get(
                            option['name'])) - set(option['values']))
                        shopify_missing_options.update(
                            {option['name']: missing_values}) if missing_values else shopify_missing_options.update({})
            _logger.info("shopify_missing_options ===>>>{}".format(
                shopify_missing_options))

            if product_data.get('product', {}).get('variants'):
                shopify_ids = [variant['id'] for variant in product_data.get(
                    'product', {}).get('variants')]
                odoo_shopify_ids = [int(i) for i in list(
                    filter(bool, self.product_variant_ids.mapped('shopify_id')))]
                # odoo_variants_to_update = list(set(shopify_ids) - set(odoo_shopify_ids))
                odoo_variants_to_update = list(
                    set(shopify_ids).difference(odoo_shopify_ids))
                odoo_variants_to_remove = list(
                    set(odoo_shopify_ids).difference(shopify_ids))

                _logger.info(
                    "Length of shopify_ids ===>>>{}".format(len(shopify_ids)))
                _logger.info("Length of odoo_shopify_ids ===>>>{}".format(
                    len(odoo_shopify_ids)))
                _logger.info("Length of odoo_variants_to_update ===>>>{}".format(
                    len(odoo_variants_to_update)))
                _logger.info("Length of odoo_variants_to_remove ===>>>{}".format(
                    len(odoo_variants_to_remove)))

                if odoo_variants_to_update:
                    _logger.info("UPDATE THE ODOO PRODUCT VARIANTS")
                    _logger.info("NOT REQUIRED FOR FAIRECHILD")

                if odoo_variants_to_remove:
                    odoo_variants_to_remove_str = list(
                        map(str, odoo_variants_to_remove))
                    _logger.info(
                        "REMOVE THE SHOPIFY ID FOR THE ODOO PRODUCT VARIANTS")
                    odoo_variant_ids = self.product_variant_ids.filtered(
                        lambda varint: varint.shopify_id in odoo_variants_to_remove_str)
                    _logger.info(
                        "odoo_variant_ids ===>>>{}".format(odoo_variant_ids))
                    _logger.info("Length of odoo_variant_ids ===>>>{}".format(
                        len(odoo_variant_ids)))

        return odoo_variants_to_update, odoo_variants_to_remove_str

    def get_shopify_product_data(self):
        res = {}
        if self.shopify_id:
            try:
                marketplace_instance_id = self.shopify_instance_id
                if getattr(marketplace_instance_id, "use_graphql", False):
                    query = """
                    query SyncoriaProductBasic($id: ID!) {
                      product(id: $id) {
                        id
                        title
                        options { name position values }
                        variants(first: 250) {
                          nodes {
                            legacyResourceId
                            sku
                            inventoryItem { legacyResourceId }
                          }
                        }
                      }
                    }
                    """
                    gql, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=query,
                        variables={"id": to_shopify_gid("Product", self.shopify_id)},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if gql.get("errors"):
                        raise UserError(_("Exception: {}".format(gql.get("errors"))))
                    p = ((gql.get("data") or {}).get("product") or {})
                    res = {
                        "product": {
                            "id": from_shopify_gid(p.get("id")),
                            "title": p.get("title"),
                            "options": p.get("options") or [],
                            "variants": [
                                {
                                    "id": int(v.get("legacyResourceId") or 0) if v.get("legacyResourceId") else None,
                                    "sku": v.get("sku"),
                                    "inventory_item_id": int(((v.get("inventoryItem") or {}).get("legacyResourceId") or 0)) if (v.get("inventoryItem") or {}).get("legacyResourceId") else None,
                                } for v in (((p.get("variants") or {}).get("nodes")) or [])
                            ],
                        }
                    }
                else:
                    raise UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            except Exception as e:
                raise UserError(_("Exception: {}".format(e.args)))
        else:
            _logger.warning("Error: Shopify Id cannot be empty!")
        return res

    def shopify_delete_product(self):
        if self.shopify_id and self.marketplace_instance_id:
            marketplace_instance_id = self.marketplace_instance_id
            try:
                if getattr(marketplace_instance_id, "use_graphql", False):
                    delete_query = """
                    mutation productDelete($input: ProductDeleteInput!) {
                      productDelete(input: $input) {
                        deletedProductId
                        userErrors { field message }
                      }
                    }
                    """
                    res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=delete_query,
                        variables={
                            "input": {
                                "id": to_shopify_gid("Product", self.shopify_id),
                            }
                        },
                        type="POST",
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if not res.get("errors"):
                        self.shopify_id = False
                        self.marketplace_instance_id = False
                    return
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            except Exception as e:
                _logger.info(e)

    def shopify_get_inventory_id_batch(self):
        for record in self:
            for variant in record.product_variant_ids:
                variant.shopify_get_inventory_id()

class ProductProductShopify(models.Model):
    _inherit = 'product.product'

    shopify_categ_ids = fields.One2many('shopify.product.category',
                                        'product_id',
                                        string="Shopify Categories")
    # shopify_id = fields.Char(string="Shopify Id", store=True, copy=False)
    # shopify_inventory_id = fields.Char(string="Shopify Inventory Id", store=True, copy=False)
    shopify_type = fields.Char(readonly=True, store=True)
    shopify_com = fields.Char()
    shopify_image_id = fields.Char(string="Shopify Image Id", store=True, copy=False)
    shopify_origin_country_id = fields.Many2one(
        string='Shopify Country Code of Origin',
        comodel_name='res.country',
        related='product_tmpl_id.shopify_origin_country_id',
        readonly=True,
    )
    shopify_province_origin_id = fields.Many2one(
        string='Shopify Province Code of Origin',
        comodel_name='res.country.state',
        related='product_tmpl_id.shopify_province_origin_id',
        readonly=True,
    )
    # Currency Conversion
    shopify_currency_id = fields.Many2one(
        string='Shopify Currency',
        comodel_name='res.currency',
        related='product_tmpl_id.shopify_currency_id',
        readonly=True,
    )
    shopify_price = fields.Float(string='Shopify Product Price', )
    inventory_stock_updated = fields.Boolean()
    shopify_qty_available = fields.Float(
        'Shopify Qty On Hand', compute='_compute_shopify_quantities',
        digits='Product Unit of Measure', compute_sudo=False,
        help="Current quantity of products.\n"
             "In a context with a single Stock Location, this includes "
             "goods stored at this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "stored in the Stock Location of the Warehouse of this Shop, "
             "or any of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    shopify_product_mapping_ids = fields.One2many('shopify.product.mappings', 'product_id', string='Instance Mappings')
    shopify_need_sync = fields.Boolean(string='Need to Sync To Shopify?')

    def _compute_shopify_quantities(self):
        products = self.filtered(lambda p: p.type != 'service')
        services = self - products
        products.shopify_qty_available = 0.0
        services.shopify_qty_available = 0.0
        instance_id = self.marketplace_instance_id
        if instance_id and instance_id.warehouse_id:
            warehouse_id = self.env['stock.warehouse'].browse(instance_id.warehouse_id.id)
            for product in products:
                product.shopify_qty_available = product.with_context({'warehouse': warehouse_id.id}).qty_available

    # Be aware that the exact same function exists in product.template
    def shopify_action_open_quants(self):
        instance_id = self.shopify_instance_id
        warehouse_id = instance_id.warehouse_id
        loc_domain = [('warehouse_id', '=', warehouse_id.id)]
        loc_domain += [('usage', '=', 'internal')]
        location_id = self.env['stock.location'].search([('location_id', '=', warehouse_id.id)])
        print("location_id ===>>>", location_id)

        domain = [('product_id', 'in', self.ids)]
        domain += [('location_id', 'in', [8])]
        hide_location = not self.user_has_groups('stock.group_stock_multi_locations')
        hide_lot = all(product.tracking == 'none' for product in self)
        self = self.with_context(
            hide_location=hide_location, hide_lot=hide_lot,
            no_at_date=True, search_default_on_hand=True,
        )

        # If user have rights to write on quant, we define the view as editable.
        if self.user_has_groups('stock.group_stock_manager'):
            self = self.with_context(inventory_mode=True)
            # Set default location id if multilocations is inactive
            if not self.user_has_groups('stock.group_stock_multi_locations'):
                user_company = self.env.company
                warehouse = self.env['stock.warehouse'].search(
                    [('company_id', '=', user_company.id)], limit=1
                )
                if warehouse:
                    self = self.with_context(default_location_id=warehouse.lot_stock_id.id)
        # Set default product id if quants concern only one product
        if len(self) == 1:
            self = self.with_context(
                default_product_id=self.id,
                single_product=True
            )
        else:
            self = self.with_context(product_tmpl_ids=self.product_tmpl_id.ids)
        action = self.env['stock.quant'].action_view_inventory()
        action['domain'] = domain
        action["name"] = _('Update Quantity')
        return action

    def compute_shopify_price(self,marketplace_instance_id):
        for rec in self:
            if marketplace_instance_id:
                # marketplace_instance_id = rec.marketplace_instance_id
                rec.shopify_currency_id = marketplace_instance_id.pricelist_id.currency_id.id
                if marketplace_instance_id:
                    variant_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                        lambda l: l.product_id.id == rec.id)
                    template_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                        lambda l: l.product_tmpl_id.id == rec.product_tmpl_id.id)
                    item_line = variant_line or template_line
                    if item_line:
                        rec.shopify_price = item_line.fixed_price
                        rec.message_post(
                            body="Shopify Product Price updated for Product-{} with price-{}".format(rec.name,
                                                                                                     item_line.fixed_price))
            else:
                msg = "Shopify Instance ID missing for {}".format(rec)
                _logger.warning(msg)
                # rec.message_post(body=msg)

    def get_shopify_price(self,marketplace_instance_id):
        # for rec in self:
        if marketplace_instance_id:
            # marketplace_instance_id = rec.marketplace_instance_id
            self.shopify_currency_id = marketplace_instance_id.pricelist_id.currency_id.id
            if marketplace_instance_id:
                variant_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                    lambda l: l.product_id.id == self.id)
                template_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                    lambda l: l.product_tmpl_id.id == self.product_tmpl_id.id)
                item_line = variant_line or template_line
                if item_line:
                    return item_line.fixed_price
                    # self.message_post(
                    #     body="Shopify Product Price updated for Product-{} with price-{}".format(self.name,
                    #                                                                                  item_line.fixed_price))
        return None
            # else:
            #     msg = "Shopify Instance ID missing for {}".format(rec)
            #     _logger.warning(msg)

    compare_at_price = fields.Char()
    fulfillment_service = fields.Char()
    inventory_management = fields.Char()
    inventory_policy = fields.Char()
    requires_shipping = fields.Boolean()
    taxable = fields.Boolean()
    shopify_vendor = fields.Char()
    shopify_collections = fields.Char()
    shopify_parent_id = fields.Char()

    def action_create_shopify_product(self, instance):
        mapping = self.env['shopify.product.mappings'].search([('product_id', '=', self.id), ('shopify_instance_id', '=', instance.id)], limit=1)
        data = get_protmpl_vals(self, 'create', mapping, instance)
        shopify_pt_request(self, data, 'create', mapping, instance)

    def action_update_shopify_product(self, instance):
        mapping = self.env['shopify.product.mappings'].search([('product_id', '=', self.id), ('shopify_instance_id', '=', instance.id)], limit=1)
        if not mapping:
            return
        data = get_protmpl_vals(self, 'update', mapping, instance)
        shopify_pt_request(self, data, 'update', mapping, instance)

    def action_update_odoo_cost_product(self):
        for rec in self:
            Connector = self.env['marketplace.connector']
            if getattr(rec.marketplace_instance_id, "use_graphql", False):
                query = """
                query SyncoriaInventoryItemCost($id: ID!) {
                  inventoryItem(id: $id) {
                    unitCost { amount }
                  }
                }
                """
                inventory_res, _next = Connector.shopify_graphql_call(
                    headers={'X-Service-Key': rec.marketplace_instance_id.token},
                    url='/graphql.json',
                    query=query,
                    variables={"id": to_shopify_gid("InventoryItem", rec.shopify_inventory_id)},
                    type='POST',
                    marketplace_instance_id=rec.marketplace_instance_id,
                )
                if inventory_res.get("errors"):
                    _logger.info("inventory_res errors: %s", inventory_res.get("errors"))
                    continue
                item = ((inventory_res.get("data") or {}).get("inventoryItem") or {})
                cost = ((item.get("unitCost") or {}).get("amount"))
                if cost is not None:
                    rec.standard_price = float(cost)
            else:
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))

    def action_update_shopify_cost_product(self, marketplace_instance_id):
        for rec in self:
            mapping = self.env['shopify.product.mappings'].search([('product_id', '=', self.id), ('shopify_instance_id', '=', marketplace_instance_id.id)], limit=1)
            if getattr(marketplace_instance_id, "use_graphql", False):
                # Use GraphQL inventoryItemUpdate (supports cost).
                data = {
                    "inventory_item": {
                        'id': mapping.shopify_inventory_id,
                        'cost': rec.standard_price
                    }
                }
                shopify_inventory_request(rec, data, 'update', marketplace_instance_id)
            else:
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))

    def action_update_varaint_shopify_images(self):
        for record in self:
            marketplace_instance_id = record.shopify_instance_id or get_marketplace(record)
            if getattr(marketplace_instance_id, "use_graphql", False):
                if record.image_1920 and marketplace_instance_id.set_image:
                    # Use shared GraphQL media upload + productCreateMedia flow.
                    update_image_shopify(marketplace_instance_id, record.image_1920, record.product_tmpl_id, record)
                continue
            raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))

    def action_update_inventory_item(self):
        for rec in self:
            if rec.shopify_inventory_id:
                inventory_item = {
                    "id": rec.shopify_inventory_id,
                    "sku": rec.default_code or "",
                }
                if rec.shopify_compare_price:
                    inventory_item['cost'] = rec.shopify_compare_price if rec.shopify_compare_price else None

                inventory_item['harmonized_system_code'] = rec.hs_code or ""

                if rec.product_tmpl_id and not inventory_item.get('harmonized_system_code'):
                    inventory_item['harmonized_system_code'] = rec.product_tmpl_id.hs_code or ""

                if rec.type in ['product', 'consumable']:
                    inventory_item['requires_shipping'] = True
                if rec.shopify_origin_country_id:
                    inventory_item[
                        'country_code_of_origin'] = rec.shopify_origin_country_id.code if rec.shopify_origin_country_id else None
                    # if inventory_item.get('harmonized_system_code'):
                    #     inventory_item['country_harmonized_system_codes'] = [{
                    #                 "country_code": rec.shopify_origin_country_id.code,
                    #                 "harmonized_system_code": inventory_item['harmonized_system_code']
                    #     }]
                if rec.shopify_province_origin_id:
                    inventory_item[
                        'province_code_of_origin'] = rec.shopify_province_origin_id.code if rec.shopify_province_origin_id else None

                inventory_item = {k: v for k, v in inventory_item.items() if v}
                data = {"inventory_item": inventory_item}
                # data = {k: v for k, v in data.items() if v}
                _logger.info("data====>>>>%s" % data)
                res = shopify_inventory_request(rec, data, 'update')
                _logger.info("RES====>>>>%s" % res)

                if inventory_item.get('harmonized_system_code'):
                    rec.write({'hs_code': inventory_item.get('harmonized_system_code')})
            else:
                rec.message_post(
                    body=_("Shopify Inventory Id is Empty for Product-%s" % (rec.id)))

    def shopify_get_inventory_id(self):
        if self.shopify_id and self.marketplace_instance_id:
            marketplace_instance_id = self.marketplace_instance_id
            try:
                if getattr(marketplace_instance_id, "use_graphql", False):
                    query = """
                    query SyncoriaVariantInventoryItem($id: ID!) {
                      productVariant(id: $id) {
                        legacyResourceId
                        product { legacyResourceId }
                        inventoryItem { legacyResourceId }
                      }
                    }
                    """
                    res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=query,
                        variables={"id": to_shopify_gid("ProductVariant", self.shopify_id)},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if res.get("errors"):
                        return
                    v = ((res.get("data") or {}).get("productVariant") or {})
                    inv_id = (v.get("inventoryItem") or {}).get("legacyResourceId")
                    prod_id = (v.get("product") or {}).get("legacyResourceId")
                    if inv_id:
                        self.shopify_inventory_id = str(inv_id)
                    if prod_id:
                        self.shopify_parent_id = str(prod_id)
                else:
                    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            except Exception as e:
                _logger.info(e)

    def shopify_get_inventory_id_batch(self):
        for record in self:
            record.shopify_get_inventory_id()

    def shopify_delete_variant(self):
        if not self.shopify_parent_id:
            raise UserError('You must have Shopify parent product id to delete the variant')
        if self.shopify_id and self.marketplace_instance_id and self.shopify_parent_id:
            marketplace_instance_id = self.marketplace_instance_id
            try:
                if getattr(marketplace_instance_id, "use_graphql", False):
                    mutation = """
                    mutation SyncoriaProductVariantDelete($id: ID!) {
                      productVariantDelete(id: $id) {
                        deletedProductVariantId
                        userErrors { field message }
                      }
                    }
                    """
                    res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=mutation,
                        variables={"id": to_shopify_gid("ProductVariant", self.shopify_id)},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if res.get("errors"):
                        return
                    payload = (res.get("data") or {}).get("productVariantDelete") or {}
                    if payload.get("userErrors"):
                        return
                    if payload.get("deletedProductVariantId"):
                        self.shopify_parent_id = False
                        self.shopify_id = False
                        self.shopify_inventory_id = False
                        self.marketplace_instance_id = False
                else:
                    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            except Exception as e:
                _logger.info(e)


class ProductCategShopify(models.Model):
    _inherit = 'product.category'

    shopify_id = fields.Integer(string="Shopify ID", readonly=True, store=True)


class ShopifyCategory(models.Model):
    _name = 'shopify.product.category'
    _description = 'shopify Product Category'
    _rec_name = 'categ_name'

    name = fields.Many2one('product.category', string="Category")
    categ_name = fields.Char(string="Actual Name")
    product_tmpl_id = fields.Many2one('product.template', string="Product Template Id")
    product_id = fields.Many2one('product.product')


# class ProductAttributeExtended(models.Model):
#     _inherit = 'product.attribute'
#
#     attribute_set_id = fields.Integer(string="Ids")
#     # attribute_set = fields.Many2one('product.attribute.set')
#
# class SCPQ(models.TransientModel):
#     _inherit = 'stock.change.product.qty'
#
#


class ProductTemplateAttributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    shopify_value_ids = fields.Many2many('product.attribute.value',
                                         string="Shopify Exclude Values",
                                         domain="[('attribute_id', '=', attribute_id)]",
                                         relation='shopify_pav_ptal_rel',
                                         ondelete='restrict')

#     shopify_value_count = fields.Integer(compute='_compute_shopify_value_count', store=True, readonly=True)
#
#     @api.depends('shopify_value_ids')
#     def _compute_shopify_value_count(self):
#         for record in self:
#             record.shopify_value_count = len(record.shopify_value_ids)
#
#     web_excl_value_ids = fields.Many2many('product.attribute.value', string="Website Exclude Values", domain="[('attribute_id', '=', attribute_id)]",
#         relation='webexcl_pav_ptal_rel', ondelete='restrict')


# class ShopifyProductCollection(models.Model):
#     _name = 'shopify.product.collection'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _description = 'Shopify Product Collection'

#     _rec_name = 'title'
#     _order = 'title ASC'

#     title = fields.Char(
#         string='Title',
#         required=True,
#         default=lambda self: _('New'),
#         copy=False,
#         size=255,
#     )
#     body_html = fields.Text(copy=False)
#     handle = fields.Char(copy=False)
#     image_id = fields.Many2one(comodel_name='ir.attachment', ondelete='set null', copy=False)
#     shopify_id = fields.Char('Shopify ID', copy=False)#Big Integer
#     shopify_published = fields.Boolean('Published', copy=False)
#     shopify_published_at = fields.Datetime('Shopify Published At', copy=False)
#     shopify_published_scope = fields.Selection(
#         string='Published Scope',
#         selection=[('web', 'Web'), ('global', 'Global')],
#     )
#     shopify_sort_order = fields.Selection(
#         string='Sort Order',
#         selection=[
#             ('alpha-asc', 'Alphabetically, in ascending order (A - Z).'),
#             ('alpha-desc', 'Alphabetically, in descending order (Z - A).'),
#             ('best-selling', 'By best-selling products.'),
#             ('created', 'By date created, in ascending order (oldest - newest).'),
#             ('created-desc', 'By date created, in descending order (newest - oldest).'),
#             ('manual', 'Order created by the shop owner.'),
#             ('price-asc', 'By price, in ascending order (lowest - highest).'),
#             ('price-desc', 'By price, in descending order (highest - lowest).'),
#         ],
#     )
#     shopify_template_suffix = fields.Selection(
#         selection=[('custom', 'Custom'), ('null', 'Null')],
#         default='custom',
#     )
#     shopify_updated_at = fields.Datetime()
#     product_ids = fields.Many2many(
#         string='Products',
#         comodel_name='product.template',
#         relation='product_template_shopify_collection_rel',
#         column1='product_template_id',
#         column2='shopify_collection_id',
#         domain=[('shopify_id', '!=', False)],
#     )
#     instance_id = fields.Many2one(
#         string='Marketplace Instance',
#         comodel_name='marketplace.instance',
#         ondelete='restrict',
#     )
#     collection_image = fields.Image("Collection Image", max_width=128, max_height=128)

#     def get_collection_url(self):
#         host = self.instance_id.marketplace_host
#         api_version = self.instance_id.marketplace_api_version
#         collection_id = self.shopify_id
#         url = f'{host}/admin/api/{api_version}/custom_collections/{collection_id}.json'
#         if 'http' not in url:
#             url = 'https://' + url
#         return url

#     def get_collection_products_url(self):
#         host = self.instance_id.marketplace_host
#         api_version = self.instance_id.marketplace_api_version
#         collection_id = self.shopify_id
#         url = f'{host}/admin/api/{api_version}/collections/{collection_id}/products.json'
#         if 'http' not in url:
#             url = 'https://' + url
#         return url

#     def delete_shopify_collection_product(self, product_id):
#         headers = self.get_headers()
#         host = self.instance_id.marketplace_host
#         api_version = self.instance_id.marketplace_api_version
#         url = f'{host}/admin/api/{api_version}/collects/{product_id}.json'
#         url = 'https://' + url if 'http' not in url else url

#         data = requests.delete(url=url, headers=headers)

#         if data.status_code == 200:
#             _logger.info(f"Shopify Collection Product ID-{product_id} deleted successfully!")
#         else:
#             _logger.info(f"Shopify Collection Product ID-{product_id} deletion unsuccessful")

#     def add_shopify_collection_product(self, product_id):
#         headers = self.get_headers()
#         host = self.instance_id.marketplace_host
#         api_version = self.instance_id.marketplace_api_version
#         url = f'{host}/admin/api/{api_version}/collects.json'
#         url = 'https://' + url if 'http' not in url else url

#         collect_product_dict = {
#             'collect' : {
#                 'product_id' : product_id,
#                 'collection_id' : self.shopify_id,
#             }
#         }

#         data = requests.post(url=url, headers=headers, data=json.dumps(collect_product_dict))

#         if data.status_code == 201:
#             _logger.info(f"Shopify Collection Product ID-{product_id} added successfully!")
#         else:
#             _logger.info(f"Shopify Collection Product ID-{product_id} addition unsuccessful")


#     def convert_shopify_dt_to_odoo_dt(self, shopify_dt):
#         timeformat = shopify_dt.split('+')[-6:]
#         odoo_dt = shopify_dt[0:-6].replace('T',' ')
#         return odoo_dt

#     def get_headers(self):
#         headers = {}
#         headers['X-Shopify-Access-Token'] = self.instance_id.marketplace_api_password
#         headers['Content-Type'] = 'application/json'
#         return headers

#     def convert_odoo_collection_to_shopify_dictionary(self):
#         collection_dict = {}
#         collection_dict.update({
#             'custom_collection' : {
#                 'id' : self.shopify_id,
#                 'body_html' : self.body_html,
#             }
#         })
#         return collection_dict

#     def convert_shopify_collection_to_odoo_dictionary(self, collection_read):
#         collection_dict = {}

#         if collection_read.get('title'):
#             collection_dict['title'] = collection_read.get('title')
#         if collection_read.get('body_html'):
#             collection_dict['body_html'] = collection_read.get('body_html')
#         if collection_read.get('handle'):
#             collection_dict['handle'] = collection_read.get('handle')
#         if collection_read.get('id'):
#             collection_dict['shopify_id'] = collection_read.get('id')
#         if collection_read.get('published'):
#             collection_dict['shopify_published'] = collection_read.get('published')
#         if collection_read.get('published_at'):
#             collection_dict['shopify_published_at'] = self.convert_shopify_dt_to_odoo_dt(collection_read.get('published_at'))
#         if collection_read.get('published_scope'):
#             collection_dict['shopify_published_scope'] = collection_read.get('published_scope')
#         if collection_read.get('sort_order'):
#             collection_dict['shopify_sort_order'] = collection_read.get('sort_order')
#         if collection_read.get('template_suffix'):
#             collection_dict['shopify_template_suffix'] = collection_read.get('template_suffix')
#         if collection_read.get('updated_at'):
#             collection_dict['shopify_updated_at'] = self.convert_shopify_dt_to_odoo_dt(collection_read.get('updated_at'))

#         return collection_dict

#     def get_shopify_collection_data(self):
#         url = self.get_collection_url()
#         headers = self.get_headers()
#         data = requests.get(url=url, headers=headers)

#         if data.status_code == 200:
#             data = data.json()
#             return data

#         return False

#     def shopify_import_collection_data(self):
#         if self.instance_id and self.shopify_id:
#             collection_data = self.get_shopify_collection_data()

#             if collection_data.get('custom_collection'):

#                 collection_read = collection_data.get('custom_collection')
#                 collection_dict = self.convert_shopify_collection_to_odoo_dictionary(collection_read)

#                 if collection_dict:
#                     self.write(collection_dict)

#                     self.import_shopify_collection_products(self.instance_id, self.shopify_id)
#                     self.message_post(body=_(f"Collection Id- {self.shopify_id} successfully imported in Odoo."))

#             return False


#     def shopify_import_collection_products_data(self):
#         if self.instance_id and self.shopify_id:
#             url = self.get_collection_products_url()
#             headers = self.get_headers()
#             data = requests.get(url=url, headers=headers)

#             if data.status_code == 200:
#                 data = data.json()
#                 return data

#             return False


#     def shopify_import_collection(self):
#         collection_read = self.shopify_import_collection_data()
#         if collection_read:
#             self.import_shopify_collection_products(self.instance_id, self.shopify_id)
#         else:
#             print("No Collection data imported!")

#     def shopify_export_collection(self):
#         if self.instance_id and self.shopify_id:
#             try:
#                 url = self.get_collection_url()
#                 headers = self.get_headers()
#                 collection_dict = self.convert_odoo_collection_to_shopify_dictionary()
#                 data = requests.put(url=url, headers=headers, data=json.dumps(collection_dict))

#                 if data.status_code == 200:
#                     data = data.json()
#                     products_data = self.shopify_import_collection_products_data()

#                     shopify_product_ids = []
#                     shopify_product_ids_dict = {}
#                     if products_data:
#                         shopify_product_ids
#                         if products_data.get('products'):
#                             for product in products_data['products']:
#                                 if product.get('options'):
#                                     for option in product.get('options'):
#                                         shopify_product_ids += [str(option['product_id'])]
#                                         shopify_product_ids_dict[str(option['product_id'])] = str(product.get('id'))

#                         odoo_product_ids = self.product_ids.mapped('shopify_id')

#                         needs_to_add_products = list(set(odoo_product_ids) - set(shopify_product_ids))
#                         needs_to_delete_products  = list(set(shopify_product_ids) - set(odoo_product_ids))


#                         for product_id in needs_to_delete_products:
#                             product_id = shopify_product_ids_dict.get(product_id)
#                             self.delete_shopify_collection_product(product_id)

#                         for product_id in needs_to_add_products:
#                             self.add_shopify_collection_product(product_id)


#                     if data.get('custom_collection'):
#                         self.message_post(body=_("Collection updated successfully on Shopify"))
#                     else:
#                         raise UserError(_("No Custom Collections found in Shopify"))
#                 else:
#                     raise UserError(_("Error: {}".format(data.text)))

#             except Exception as e:
#                 raise UserError(_("Error: {}".format(e.args)))


#     def import_shopify_collection_products(self, instance_id, collection_id):
#         products_data = self.shopify_import_collection_products_data()

#         if products_data:
#             if products_data.get('products'):
#                 products = products_data.get('products') if type(
#                     products_data['products']) == list else [products_data['products']]

#                 _logger.info(f"Number of Collection Productions for Collection ID: {collection_id} - {len(products)}")

#                 products_ids = [product['id'] for product in products]

#                 for product_id in products_ids:    
#                     product_tmpl_id = self.env['product.template'].search([('shopify_id', '=', product_id)], limit=1)
#                     if product_tmpl_id:
#                         if str(product_id) not in self.product_ids.mapped('shopify_id'):
#                             self.product_ids = self.product_ids.ids + product_tmpl_id.ids


#             else:
#                 raise UserError(
#                     _("No Custom Collections found in Shopify"))


#     def process_shopify_collection_product(self, products_read, collection_id):
#         if products_read.get('id'):
#             product_template = self.env['product.template']

#             if str(products_read.get('id')) not in collection_id.product_ids.mapped('shopify_id'):
#                 product_tmpl_id = product_template.search([('shopify_id', '=', products_read.get('id'))], limit=1)

#                 if product_tmpl_id:
#                     collection_id.product_ids =  collection_id.product_ids.ids + product_tmpl_id.ids
#                     collection_id._cr.commit()


# class IrAttachment(models.Model):
#     _inherit = 'ir.attachment'

#     shopify_attachment = fields.Binary()
#     src = fields.Char()
#     alt = fields.Char()
#     shopify_created_at = fields.Datetime()
#     shopify_width = fields.Integer()
#     shopify_height = fields.Integer()
#     shopify_collection_id = fields.Many2one(comodel_name='shopify.product.collection',  ondelete='set null')

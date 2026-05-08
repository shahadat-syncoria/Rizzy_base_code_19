# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import requests
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)


class ShopifyFeedProducts(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.products'
    _description = 'Shopify Feed Products'

    _rec_name = 'title'
    _order = 'name DESC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.products'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    parent = fields.Boolean(default=False)
    title = fields.Char(copy=False)
    shopify_id = fields.Char(string='Shopify Id', readonly=True)
    inventory_id = fields.Char(string='Inventory Id', readonly=True)
    product_data = fields.Text(
        string='Product Data',
    )
    state = fields.Selection(
        string='State',
        tracking=True,
        selection=[('draft', 'draft'), ('queue', 'Queue'),
                   ('processed', 'Processed'), ('failed', 'Failed')]
    )
    product_id = fields.Many2one(
        string='Product Variant',
        comodel_name='product.product',
        ondelete='restrict',
    )
    product_tmpl_id = fields.Many2one(
        string='Product Template',
        comodel_name='product.template',
        ondelete='restrict',
    )
    # product_wiz_id = fields.Many2one(
    #     string='Product Wiz',
    #     comodel_name='feed.products.fetch.wizard',
    #     ondelete='restrict',
    # )
    barcode = fields.Char()
    default_code = fields.Char('Default Code(SKU)')
    feed_varaint_ids = fields.One2many(
        string='Feed Variants',
        comodel_name='shopify.feed.products',
        inverse_name='parent_id',
    )
    feed_variant_count = fields.Integer(compute="_compute_feed_variant_count")
    
    @api.depends('feed_varaint_ids')
    def _compute_feed_variant_count(self):
        for record in self:
            record.feed_variant_count = len(record.feed_varaint_ids)

    def action_view_feed_variant(self):
        self.ensure_one()
        linked_child_varinats = self.mapped('feed_varaint_ids')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Feed Child Products'),
            'res_model': 'shopify.feed.products',
            'view_mode': 'list,form',
            'domain': [('id', 'in', linked_child_varinats.ids)],
        }

    parent_id = fields.Many2one(
        string='Parent Product',
        comodel_name='shopify.feed.products',
        domain=[('parent','=',True)]
    )
    parent_title = fields.Char()
    

    @api.onchange('product_tmpl_id')
    def _onchange_product_tmpl_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id and self.product_tmpl_id:
            raise UserError(_("Only one can be added"))

    def update_product_product(self):
        _logger.info("update_product_product")
        if self.product_id:
            self.product_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })

    def update_product_template(self):
        _logger.info("update_product_template")
        if self.product_tmpl_id:
            self.product_tmpl_id.write({
                'shopify_id' : self.shopify_id,
                'shopify_inventory_id' : self.inventory_id,
                'marketplace_type' : 'shopify',
            })

    def process_feed_products(self):
        for record in self:
            record.process_feed_product()

    # TO DO: Feed Products to Odoo Products
    def process_feed_product(self):
        """Convert Shopify Feed Product to Odoo Product"""
        for rec in self:
            config_products = json.loads(rec.product_data)
            # if config_products.get('status') != 'active':
            #     return
            categ_list = []
            existing_prod_ids = []
            try:
                attributes = {}
                attributes['items'] = []

                simple_products = {}
                simple_products['items'] = []

                if config_products.get('product_type') not in categ_list and config_products.get('product_type') != '':
                    categ_list.append(config_products.get('product_type'))

                try:
                    self.shopify_update_categories(categ_list)
                except Exception as e:
                    _logger.warning("Exception occured %s", e)
                    raise UserError(_("Error Occured %s") % e)

                if len(config_products.get('variants')) == 1:
                    simple_products['items'].append(config_products)

                if config_products.get('options'):
                    for option in config_products.get('options'):
                        attribute = {}
                        attribute['attribute_id'] = str(option.get('id'))
                        attribute['label'] = str(option.get('name'))
                        attribute['attribute_code'] = str(option.get('name'))
                        attribute['options'] = option.get('values')
                        attributes['items'].append(attribute)

                tmpl_vals = self.find_default_vals('product.template')
                product_type = 'configurable_product' if len(config_products.get('variants')) > 1 else 'simple_product'
                config_products = [config_products]
                self._shopify_import_products_list(config_products,
                                          existing_prod_ids,
                                          tmpl_vals,
                                          attributes,
                                          self.instance_id,
                                          product_type)
            except Exception as e:
                _logger.warning("Exception occured: %s", e)
                raise UserError(_("Error Occured %s") % e)

    def shopify_update_categories(self, categ_list):
        """Updating category list from shopify to odoo"""
        for categ in categ_list:
            if not self.env['product.category'].search([('name', '=', categ)]):
                self.env['product.category'].create({
                    'name': categ,
                    'parent_id': None,
                })
        return

    def _get_product_id(self, shopify_product_val):
        product_skus = list(map(lambda x: x['sku'], shopify_product_val.get("variants")))
        if '' in product_skus:
            product_skus.remove('')

        product_tmpl_id = self.env['product.product'].search([
            ('default_code', 'in', product_skus),
        ]).product_tmpl_id
        if len(product_tmpl_id) > 1:
            name = []
            for prod in product_tmpl_id:
                name.append(prod.name)
            raise Exception("Product Variants belong to different templates. Template Id: {}. Template Name: {}".format(product_tmpl_id, name))

        return product_tmpl_id

    """ PRODUCT SYNC """
    def _shopify_import_products_list(self,
                                      config_products,
                                      existing_prod_ids,
                                      template,
                                      attributes,
                                      instance_id,
                                      product_type
                                      ):
        """
            The aim of this function is to configure all the
            configurable products with their variants
            config_products: configurable products list from shopify with their childs
            existing_prod_ids: products synced with shopify
            template: required fields with their values for product template
            attributes: complete list of attributes from shopify
        """

        VariantObj = self.env['product.product']
        cr = self.env.cr
        # fetching all the attributes and their values
        # dictionary of lists with attributes, values and id from shopify
        # if this attribute is not synced with odoo, we will do it now
        cr.execute("select id, name from product_attribute where "
                   " name is not null")
        all_attrib = cr.fetchall()

        odoo_attributes = {}
        for j in all_attrib:
            if j[1] and j[0]:
                odoo_attributes[j[1].get('en_US')] = j[0]

        attributes_list = {}
        for att in attributes['items']:
            if att['attribute_code'] in odoo_attributes:
                # existing attribute
                attributes_list[str(att['attribute_id'])] = {
                    # id of the attribute in odoo
                    'id': odoo_attributes[att['attribute_code']],
                    'code': att['attribute_code'],  # label
                    'options': {}
                }

        # update attribute values
        cr.execute("select id, name from product_attribute_value "
                   " where name is not null")
        all_attrib_vals = cr.fetchall()

        odoo_attribute_vals = {}
        for j in all_attrib_vals:
            if j[1] and j[0]:
                odoo_attribute_vals[j[1].get('en_US')] = j[0]

        for att in attributes['items']:
            for option in att['options']:
                if option != '' and option != None \
                        and option in odoo_attribute_vals \
                        and str(att['attribute_id']) in attributes_list:
                    value_rec = odoo_attribute_vals[option]
                    attributes_list[str(att['attribute_id'])]['options'][
                        option] = value_rec

        # product_ids = self.env['product.product'].search([('custom_option', '=', True)])
        # default_code_lst = []
        # cust_list = product_ids.mapped('default_code')

        # now the attributes list should be a dictionary with all the attributes
        # with their id and values both in odoo and shopify+++++

        _logger.info("START===>>>")
        for product in config_products:
            _logger.info(product)
            if str(product['id']) not in existing_prod_ids:
                try:
                    product_categ_ids = []
                    if product.get('product_type'):
                        product_categ_ids = [product.get('product_type')] or []

                    # getting odoo's category id from the shopify categ id
                    # (which is already created)
                    c_ids = []
                    if product_categ_ids:
                        cr.execute("select name from product_category "
                                   "where name in %s",
                                   (tuple(product_categ_ids),))
                        c_ids = cr.fetchall()

                    template['name'] = product['title']
                    # template['shopify_id'] = str(product['id'])
                    # template['marketplace_instance_id'] = instance_id.id
                    # Product Type
                    # [consu] Consumable
                    # [service] Service
                    # [product] Storable
                    template['type'] = 'consu'
                    # template['active'] = True if product.get(
                    #     'status') == 'active' else False
                    template['sale_ok'] = True
                    template['purchase_ok'] = True
                    template['shopify_product'] = True
                    template['shopify_published_scope'] = product.get('published_scope')
                    template['shopify_tags'] = product.get('tags')
                    template['description_sale'] = product.get('body_html')
                    template['shopify_template_suffix'] = product.get(
                        'template_suffix')
                    template['shopify_variants'] = str(
                        len(product.get('variants')))
                    template['shopify_vendor'] = product.get("vendor")
                    template['shopify_product_status'] = product.get('status')

                    # -------------------------------------Invoice Policy------------------------------------------------
                    marketplace_instance_id = self.instance_id
                    if marketplace_instance_id.default_invoice_policy:
                        template['invoice_policy'] = marketplace_instance_id.default_invoice_policy
                    # if marketplace_instance_id.sync_price == True:
                    #     template['list_price'] = product.get('price') or 0
                    # ---------------------------------------------------------------------------------------------------

                    if len(product.get('variants')) > 1:
                        template['shopify_type'] = 'config'
                    else:
                        template['shopify_type'] = 'simple'

                    template['custom_option'] = False
                    # New addition
                    # template['weight'] = product.get('weight') or 0
                    if product.get('product_type'):
                        categ_id = self.env['product.category'].search([('name', '=', product.get('product_type'))], limit=1)
                        if len(categ_id) > 0:
                            template['categ_id'] = categ_id.id
                    # product_tmpl_id = self.env['product.template'].sudo().search(
                    #     [('shopify_id', '=', str(product['id'])),
                    #      ('marketplace_instance_id', '=', marketplace_instance_id.id)])
                    product_tmpl_id = self.env['shopify.product.mappings'].sudo().search(
                        [('shopify_parent_id', '=', str(product['id'])), ('shopify_instance_id', '=', marketplace_instance_id.id)], limit=1).product_tmpl_id
                    if not product_tmpl_id:
                        if marketplace_instance_id.is_product_create:
                            template = self.shopify_process_options(product, template)
                            pro_tmpl = self.env['product.template'].sudo().create(template)
                            product_tmpl_id = [pro_tmpl.id]
                        else:
                            continue
                    else:
                        pro_tmpl = self.env['product.template'].browse(product_tmpl_id.id)
                        product_tmpl_id = [product_tmpl_id.id]
                    image_file = False

                    if marketplace_instance_id.sync_product_image and product_tmpl_id:
                        try:
                            if 'image' in product and product.get('image'):
                                pro_tmpl.update(
                                    {'image_1920': self.shopify_image_processing(product.get("image").get("src"))})
                        except:
                            _logger.info(
                                "unable to import image url of product sku %s", product.get('sku'))

                    if product.get('variants'):
                        # here we create template for main product and variants for
                        # the child products

                        if len(product.get('variants')) > 0:
                            # since this product has variants, we need to get the
                            # variant options associated with this product
                            # we are updating the attributes associated with this product
                            # (if it is not added to odoo already)

                            ###############################################################################
                            ###############################################################################

                            options = product.get('options')
                            for option in options:
                                option['attribute_id'] = option.get('id')

                            attrib_line = {}
                            child_file = False

                            for child in product['variants']:

                                option_keys = ['option1', 'option2', 'option3']
                                option_names = []
                                for key, value in child.items():
                                    if key in option_keys:
                                        if child[key] is not None:
                                            option_names.append(child[key])
                                domain = [("product_tmpl_id", "=", pro_tmpl.id)]
                                for option in option_names:
                                    domain += [("product_template_attribute_value_ids.name", "=", option)]
                                product_id = self.env['product.product'].search(domain, limit=1)
                                if product_id:
                                    if child.get('weight'):
                                        if product_id.uom_id.name == child['weight']:
                                            weight = child['weight']
                                        else:
                                            "Convert"
                                            # TO DO:
                                            weight = child['weight'] / 2.2

                                    barcode = None
                                    if child.get('barcode'):
                                        barcodes = self.env['product.product'].search([]).mapped(
                                            'barcode') + self.env['product.template'].search([]).mapped('barcode')
                                        if child.get('barcode') not in barcodes:
                                            barcode = child.get('barcode')

                                    if product.get('images'):
                                        image_src = []
                                        for im in product.get('images'):
                                            image_src.append(im.get("src"))
                                            # if product_id.shopify_id in im.get("variant_ids"):
                                            #     image_src.append(im.get("src"))
                                            if child['id'] in im.get("variant_ids"):
                                                image_src.append(im.get("src"))

                                        if len(image_src) >= 1:
                                            child_file = image_src[0]
                                        else:
                                            child_file = False

                                    product_datas = {
                                        # 'marketplace_instance_id': instance_id.id,
                                        # 'shopify_id': str(child['id']),
                                        # 'shopify_parent_id': str(child['product_id']),
                                        'list_price': str(child['price']),
                                        'lst_price': str(child['price']),
                                        'default_code': child['sku'],
                                        'inventory_policy': child['inventory_policy'],
                                        'compare_at_price': child['compare_at_price'],
                                        'shopify_compare_price': child['compare_at_price'],
                                        'fulfillment_service': child['fulfillment_service'],
                                        'inventory_management': child['inventory_management'],
                                        'shopify_charge_tax': child['taxable'],
                                        'barcode': barcode,
                                        'shopify_image_id': child['image_id'],
                                        # 'shopify_inventory_id': child['inventory_item_id'],
                                        'shopify_type': 'simple',
                                        'requires_shipping': child['requires_shipping'],
                                        'weight': child['weight']
                                    }

                                    if marketplace_instance_id.sync_product_image and child_file:
                                        product_datas['image_1920'] = self.shopify_image_processing(child_file)
                                    product_id.write(product_datas)
                                    prod_mapping = self.env['shopify.product.mappings'].sudo().search([('product_id', '=', product_id.id), ('shopify_instance_id', '=', self.instance_id.id)])
                                    val_dict = {
                                        'name': child['sku'],
                                        'shopify_instance_id': marketplace_instance_id.id,
                                        'product_id': product_id.id,
                                        'shopify_id': child['id'],
                                        'shopify_parent_id': child['product_id'],
                                        'shopify_inventory_id': child['inventory_item_id']
                                    }
                                    if not prod_mapping:
                                        prod_mapping = self.env['shopify.product.mappings'].sudo().create(val_dict)

                    # else:
                    #     image_file = False
                    #     for pic in product['images']:
                    #         if 'src' in pic:
                    #             image_file = pic.get('src')
                    #
                    #     prod_vals = {
                    #         'product_tmpl_id': product_tmpl_id[0],
                    #         'marketplace_type': 'shopify',
                    #         'marketplace_instance_id': instance_id.id,
                    #         'shopify_id': str(product['id']),
                    #         'default_code': product.get('sku'),
                    #         'shopify_type': product.get('type_id') or 'simple',
                    #         'custom_option': False,
                    #         'combination_indices': self.get_variant_combs(child),
                    #     }
                    #     if marketplace_instance_id.sync_product_image == True:
                    #         prod_vals['image_1920'] = self.shopify_image_processing(
                    #             image_file)
                    #
                    #     if not VariantObj.sudo().search([('shopify_id', '=', str(product['id']))]):
                    #         prod_id = VariantObj.sudo().create(prod_vals)
                    #
                    #     _logger.info("product created %s", prod_id)
                    #     prod_id and existing_prod_ids.append(
                    #         str(product['id']))

                    print("Variants creation Ends")
                    self.write({"state":'processed',"product_tmpl_id":pro_tmpl or None})

                    self.env.cr.commit()

                except Exception as e:
                    self.write({"state": 'failed'})
                    self.message_post(body="Exception-{}".format(e.args))
                    _logger.warning("Exception-{}".format(e.args))
            else:

                product_obj = self.env['product.template']
                current_product = product_obj.search([("shopify_id", "=", str(product['id']))])
                current_product.write({"shopify_instance_id": instance_id.id})
                if product_type == 'configurable_product':
                    current_product.product_variant_ids.write({"shopify_instance_id": instance_id.id})
            # product_tmpl_id = self.env['product.template'].search([("shopify_id", "=", str(product['id']))])
            # product_tmpl_id.action_update_odoo_cost_product()

    def find_default_vals(self, model_name):
        """
        Finds the default, required, database persistant fields for the model provided.
        Useful for creating records using query.
        """
        cr = self.env.cr
        cr.execute("select id from ir_model "
                   "where model=%s",
                   (model_name,))
        model_res = cr.fetchone()

        if not model_res:
            return
        cr.execute("select name from ir_model_fields "
                   "where model_id=%s and required=True "
                   " and store=True",
                   (model_res[0],))
        res = cr.fetchall()
        fields_list = [i[0] for i in res if res] or []
        Obj = self.env[model_name]
        default_vals = Obj.default_get(fields_list)

        return default_vals


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

    def shopify_image_processing(self, image_url):
        if image_url:
            image = False
            try:
                if requests.get(image_url).status_code == 200:
                    image = base64.b64encode(requests.get(image_url).content)
                return image
            except Exception as e:
                _logger.warning(_(""))
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
        return comb_indices

    def get_variant_combs(self, child):
        comb_indices = False
        comb_arr = []
        for key, value in child.items():
            if key in ['option1', 'option2', 'option3']:
                if child[key] != None:
                    comb_arr.append(child[key])

        domain = [('name', 'in', comb_arr)]
        comb_indices = self.env['product.attribute.value'].search(domain)
        return comb_arr, comb_indices

    def shopify_process_options(self, product, template):
        template['attribute_line_ids'] = []
        if product.get('options'):
            oprions = product.get('options')
            for option in oprions:
                PA = self.env['product.attribute']
                attribute_name = option.get('name')
                attribute_id = PA.sudo().search(
                    [('name', '=', option.get('name'))])
                if not attribute_id:
                    """Create Attribute"""
                    attribute_id = PA.sudo().create({
                        'create_variant': 'always',
                        'display_type': 'radio',
                        'name': attribute_name,
                    })

                values_ids = []
                values = option.get('values')
                for value in values:
                    PTV = self.env['product.attribute.value']
                    value_id = PTV.sudo().search(
                        [('name', '=', value),("attribute_id","=",attribute_id.id)], limit=1)
                    if not value_id:
                        value_id = PTV.sudo().create({
                            'attribute_id': attribute_id.id,
                            'name': value,
                        })
                    values_ids.append(value_id.id)

                template['attribute_line_ids'].append(
                    [0, 0,
                        {
                            'attribute_id': attribute_id.id,
                            'value_ids': [[6, False, values_ids]]
                        }
                    ])

        return template

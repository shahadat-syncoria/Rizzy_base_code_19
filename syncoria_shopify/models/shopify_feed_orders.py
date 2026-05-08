# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import requests
import base64
import re
from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timezone
import logging
_logger = logging.getLogger(__name__)


def get_address_vals(env, address):
    """Build res.partner child-address values from Shopify address payload."""
    address = address or {}
    country = False
    state = False

    country_domain = []
    if address.get("country_code"):
        country_domain += [("code", "=", address.get("country_code"))]
    elif address.get("country"):
        country_domain += [("name", "=", address.get("country"))]
    if country_domain:
        country = env["res.country"].sudo().search(country_domain, limit=1)

    state_domain = [("country_id", "=", country.id)] if country else []
    if address.get("province_code"):
        state_domain += [("code", "=", address.get("province_code"))]
    elif address.get("province"):
        state_domain += [("name", "=", address.get("province"))]
    if state_domain:
        state = env["res.country.state"].sudo().search(state_domain, limit=1)

    return {
        "name": address.get("name") or (
            ((address.get("first_name") or address.get("firstName") or "") + " " +
             (address.get("last_name") or address.get("lastName") or "")).strip()
        ),
        "street": address.get("address1") or "",
        "street2": address.get("address2") or "",
        "city": address.get("city") or "",
        "zip": address.get("zip") or "",
        "phone": address.get("phone") or "",
        "company_name": address.get("company") or "",
        "country_id": country.id if country else None,
        "state_id": state.id if state else None,
        "shopify_add_id": address.get("id"),
        "group_rfq": False,
        "group_on": False,
    }


class ShopifyFeedOrders(models.Model):
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _name = 'shopify.feed.orders'
    _description = 'Shopify Feed Orders'

    _rec_name = 'name'
    _order = 'name DESC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.feed.orders'))
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=True)
    order_data = fields.Text(readonly=True)
    state = fields.Selection(
        string='State',
        tracking=True,
        selection=[('draft', 'Draft'), 
                   ('queue', 'Queue'),
                   ('processed', 'Processed'), 
                   ('failed', 'Failed')]
    )
    # order_wiz_id = fields.Many2one(
    #     string='Order Wiz',
    #     comodel_name='feed.orders.fetch.wizard',
    #     ondelete='restrict',
    # )
    shopify_webhook_call = fields.Boolean(string='Webhook Call', readonly=True)
    shopify_app_id = fields.Char(string='App Id', readonly=True)
    shopify_confirmed = fields.Char(string='Confirmed', readonly=True)
    shopify_contact_email = fields.Char(string='Contact Email', readonly=True)
    shopify_currency = fields.Char(string='Currency', readonly=True)
    shopify_customer_name = fields.Char(string='Customer Name', readonly=True)
    shopify_customer_id = fields.Char(string='Customer ID', readonly=True)
    shopify_gateway = fields.Char(string='Gateway', readonly=True)
    shopify_order_number = fields.Char(string='Order Number', readonly=True)
    shopify_financial_status = fields.Char(string='Financial Status', readonly=True)
    shopify_fulfillment_status = fields.Char(string='Fulfillment Status', readonly=True)
    shopify_line_items = fields.Char(string='Line Items', readonly=True)
    shopify_user_id = fields.Char(string='User ID', readonly=True)
    sale_id = fields.Many2one(
        string='Odoo Order',
        comodel_name='sale.order',
        ondelete='set null',
    )

    def compute_price_unit(self, product_id, price_unit):
        item_price = price_unit
        marketplace_instance_id = self.instance_id
        pricelist_id = marketplace_instance_id.pricelist_id
        pricelist_price = marketplace_instance_id.compute_pricelist_price
        if pricelist_price and pricelist_id and 'product.product' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.product_tmpl_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        if pricelist_price and pricelist_id and 'product.template' in str(product_id):
            item_line = marketplace_instance_id.pricelist_id.item_ids.filtered(
                lambda l: l.product_tmpl_id.id == product_id.id)
            if not item_line:
                _logger.warning("No Item Line found for {}".format(product_id))
            item_price = item_line.fixed_price if item_line else item_price
        return item_price


    def populate_shopify_order_number(self):
        for rec in self:
            if rec.order_data:
                import json
                order_json = json.loads(rec.order_data)
                if not rec.shopify_order_number:
                    rec.shopify_order_number = order_json['order_number']

    def shopify_customer(self, values, env, shipping=False):
        customer={}
        customer['name']=(values.get(
            'first_name') or "") + " " + (values.get('last_name') or "")
        customer['autopost_bills'] = 'ask'
        customer['display_name']=customer['name']
        customer['phone']=values.get('phone') or ""
        customer['email']=values.get('email') or ""
        customer['shopify_id']=values.get('id') or ""
        customer['marketplace_instance_id']=self.instance_id.id
        customer['active']=True
        customer['type']='contact'
        customer['shopify_accepts_marketing']=values.get(
            'shopify_accepts_marketing')
        customer['shopify_last_order_id']=values.get(
            'last_order_id')
        customer['shopify_last_order_name']=values.get(
            'last_order_name')
        customer['marketing_opt_in_level']=values.get(
            'marketing_opt_in_level')
        customer['multipass_identifier']=values.get(
            'multipass_identifier')
        customer['orders_count']=values.get('orders_count')
        customer['shopify_state']=values.get('state')
        customer['comment']=values.get('note')
        customer['shopify_tax_exempt']=values.get('tax_exempt')

        customer['shopify_total_spent']=values.get(
            'total_spent')
        customer['shopify_verified_email']=values.get(
            'verified_email')

        if values.get('default_address') or values.get('addresses'):
            default_address=values.get(
                'default_address') or values.get('addresses')[0]
        else:
            default_address=values
        country=False
        state=False

        if default_address:
            if default_address.get('company'):
                customer['shopify_company_name']=default_address.get('company')

            customer['street']=default_address.get(
                'address1') or ""
            customer['street2']=default_address.get(
                'address2') or ""
            customer['city']=default_address.get('city') or ""

            search_domain=[]
            if default_address.get('country_code'):
                search_domain += [('code', '=', default_address.get('country_code'))]

            elif default_address.get('country'):
                search_domain += [('name', '=', default_address.get('country'))]
            if len(search_domain) > 0:
                country=env['res.country'].sudo().search(search_domain, limit=1)
                customer['country_id']=country.id if country else None
                state_domain=[('country_id', '=', country.id)] if country else []
                if default_address.get('province_code'):
                    state_domain += [('code', '=', default_address.get('province_code'))]

                elif default_address.get('province'):
                    state_domain += [('name', '=', default_address.get('province'))]

                state=env['res.country.state'].sudo().search(state_domain, limit=1)

                customer['state_id']=state.id if state else None
            customer['zip']=default_address.get('zip') or ""

        return customer

    def get_partner_invoice_id(self, sp_order_dict, partner_id):
        res_partner = self.env['res.partner'].sudo()
        partner_invoice_id = partner_id
        if sp_order_dict.get('billing_address'):
            billing_address = sp_order_dict.get('billing_address', {})
            country_domain = []
            if billing_address.get('country_code'):
                country_domain += [('code', '=', billing_address.get('country_code'))]

            elif billing_address.get('country'):
                country_domain += [('name', '=', billing_address.get('country'))]
            country_id = self.env['res.country'].sudo().search(country_domain, limit=1)

            state_domain = [('country_id', '=', country_id.id)] if country_id else []
            if billing_address.get('province_code'):
                state_domain += [('code', '=', billing_address.get('province_code'))]
            elif billing_address.get('province'):
                state_domain += [('name', '=', billing_address.get('province'))]
            state_id = self.env['res.country.state'].sudo().search(state_domain, limit=1)

            partner_invoice_id = partner_id.child_ids.filtered(lambda l:l.type == 'invoice' and l.street.lower() == billing_address.get('address1', '').lower() and l.zip.lower() == billing_address.get('zip', '').lower() and l.phone == billing_address.get('phone', ''))
            if len(partner_invoice_id) > 1:
                partner_invoice_id = partner_invoice_id[0]
            if partner_invoice_id:
                
                partner_invoice_id.write({
                    'name': billing_address.get('name', None),
                    'street': billing_address.get('address1'),
                    'street2': billing_address.get('address2'),
                    'zip': billing_address.get('zip'),
                    'phone': billing_address.get('phone'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': billing_address.get('city'),
                    'parent_id': partner_id.id,
                    'type': 'invoice'
                })
            else:
                partner_invoice_id = res_partner.create({
                    'name': billing_address.get('name', None),
                    'street': billing_address.get('address1'),
                    'street2': billing_address.get('address2'),
                    'zip': billing_address.get('zip'),
                    'phone': billing_address.get('phone'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': billing_address.get('city'),
                    'parent_id': partner_id.id,
                    'type': 'invoice'
                })

            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_receivable_id:
                partner_invoice_id.property_account_receivable_id = partner_id.property_account_receivable_id.id
            if partner_id and partner_invoice_id and not partner_invoice_id.property_account_payable_id:
                partner_invoice_id.property_account_payable_id = partner_id.property_account_payable_id.id

        # try:
        #     self._cr.commit()
        # except Exception as e:
        #     _logger.warning("Exception-{}".format(e.args))
        return partner_invoice_id

    def get_partner_shipping_id(self, sp_order_dict, partner_id):
        res_partner = self.env['res.partner'].sudo()
        partner_shipping_id = partner_id
        if sp_order_dict.get('shipping_address'):
            shipping_address = sp_order_dict.get('shipping_address', {})
            country_domain = []
            if shipping_address.get('country_code'):
                country_domain += [('code', '=', shipping_address.get('country_code'))]

            elif shipping_address.get('country'):
                country_domain += [('name', '=', shipping_address.get('country'))]
            country_id = self.env['res.country'].sudo().search(country_domain, limit=1)

            state_domain = [('country_id', '=', country_id.id)] if country_id else []
            if shipping_address.get('province_code'):
                state_domain += [('code', '=', shipping_address.get('province_code'))]
            elif shipping_address.get('province'):
                state_domain += [('name', '=', shipping_address.get('province'))]
            state_id = self.env['res.country.state'].sudo().search(state_domain, limit=1)
            partner_shipping_id = partner_id.child_ids.filtered(lambda l:l.type == 'delivery' and l.street.lower() == shipping_address.get('address1', '').lower() and l.zip.lower() == shipping_address.get('zip', '').lower() and l.phone == shipping_address.get('phone', ''))
            if len(partner_shipping_id) > 1:
                partner_shipping_id = partner_shipping_id[0]
            if partner_shipping_id:
                partner_shipping_id.write({
                    'name': shipping_address.get('name', None),
                    'street': shipping_address.get('address1'),
                    'street2': shipping_address.get('address2'),
                    'phone': shipping_address.get('phone'),
                    'zip': shipping_address.get('zip'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': shipping_address.get('city'),
                    'parent_id': partner_id.id,
                    'type': 'delivery'
                })

            else:
                partner_shipping_id = res_partner.with_context(tracking_disable=True).create({
                    'name': shipping_address.get('name', None),
                    'street': shipping_address.get('address1'),
                    'street2': shipping_address.get('address2'),
                    'zip': shipping_address.get('zip'),
                    'phone': shipping_address.get('phone'),
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'city': shipping_address.get('city'),
                    'parent_id': partner_id.id,
                    'type': 'delivery'
                })

            if partner_id and partner_shipping_id and not partner_shipping_id.property_account_receivable_id:
                partner_shipping_id.property_account_receivable_id = partner_id.property_account_receivable_id.id
            if partner_id and partner_shipping_id and not partner_shipping_id.property_account_payable_id:
                partner_shipping_id.property_account_payable_id = partner_id.property_account_payable_id.id
        # try:
        #     self._cr.commit()
        # except Exception as e:
        #     _logger.warning("Exception-{}".format(e.args))
        return partner_shipping_id

    def get_customer_id(self, sp_order_dict):
        res_partner = self.env['res.partner'].sudo()
        partner_id = False
        partner_invoice_id = False
        partner_shipping_id = False

        if sp_order_dict.get('customer'):
            customer = sp_order_dict.get('customer')
            shopify_id = customer.get('id')
            if shopify_id:
                domain = [('marketplace_instance_id', '=', self.instance_id.id)]
                domain += [('shopify_id', '=', shopify_id)]
                partner_id = res_partner.search(domain, order='id asc', limit=1)

            if not partner_id:
                customer_vals = self.shopify_customer(customer, self.env, shipping=False)
                partner_id = res_partner.create(customer_vals)

            if partner_id:
                partner_invoice_id = self.get_partner_invoice_id(sp_order_dict, partner_id)
                partner_shipping_id = self.get_partner_shipping_id(sp_order_dict, partner_id)
            #
            # try:
            #     self._cr.commit()
            # except Exception as e:
            #     _logger.warning("Exception-{}".format(e.args))
        
        return partner_id, partner_invoice_id, partner_shipping_id

    def process_feed_orders(self):
        for record in self:
            record.process_feed_order()

    """ ORDER SYNC """
    def process_feed_order(self):
        self.ensure_one()
        """Convert Shopify Feed Order to Odoo Order"""
        msg_body = ''
        error_msg_body = ''

        PartnerObj = self.env['res.partner'].sudo()
        OrderObj = self.env['sale.order'].sudo()
        ICPSudo = self.env['ir.config_parameter'].sudo()
        all_shopify_orders = self.env['sale.order'].sudo()
        for rec in self:
            try:

                log_msg = """Shopify Process Feed Order started for {}, Shopify ID-{}""".format(rec.name,
                                                                                                rec.shopify_id)
                _logger.info(log_msg)

                marketplace_instance_id = self.instance_id
                i = json.loads(rec.order_data)
                i = i.get('order') if i.get('order') else i
                order_exists = OrderObj.search([('shopify_id', '=', i.get('id')), ('marketplace_instance_id', '=', marketplace_instance_id.id)], order='id desc', limit=1)

                if not order_exists and i['confirmed'] == True:
                    # Process Only Shopify Confirmed Orders
                    # check the customer associated with the order, if the customer is new,
                    # then create a new customer, otherwise select existing record
                    msg_body += "\nShopify Order ID: {}, Customer Name: {}".format(i.get('id'), i.get('name'))
                    partner_id, partner_invoice_id, partner_shipping_id = self.get_customer_id(sp_order_dict=i)

                    if not partner_id:
                        self.message_post(body="Customer is missing for Order: {}".format(self.shopify_id))
                        partner_id = marketplace_instance_id.default_res_partner_id
                    customer_id = partner_id.id if partner_id else False

                    product_missing = False
                    order_vals = self.get_sale_order_vals(marketplace_instance_id, customer_id, i)
                    if partner_invoice_id and partner_shipping_id:
                        order_vals.update({
                            'partner_invoice_id': partner_invoice_id.id,
                            'partner_shipping_id': partner_shipping_id.id,
                        })
                    # for tax in i['tax_lines']:
                    #     search_domain = [
                    #         # ('name', 'like', tax['title']),
                    #         ('amount', '=', tax['rate'] * 100),
                    #         ('type_tax_use', '=', 'sale'),
                    #         ('marketplace_type', '=', 'shopify'),
                    #         ('active', '=', True),
                    #     ]
                    #     Tax = self.env['account.tax']
                    #     tax_ob = Tax.search(search_domain, limit=1)

                    order_line = []
                    prod_rec = []

                    for line in i['line_items']:
                        product_tax_per = 0
                        product_tax_name = ''
                        if line.get('variant_id'):
                            product_product = self.env['product.product'].sudo()
                            prod_dom = [('shopify_instance_id', '=', marketplace_instance_id.id)]
                            # if line['sku'] is not None and line['sku'] != '':
                                # prod_dom += ['|']
                                # prod_dom += [('default_code', '=', str(line['sku']))]
                            prod_dom += [('shopify_id', '=', str(line['variant_id']))]
                            prod_rec = self.env['shopify.product.mappings'].search(prod_dom, limit=1).product_id
                        elif line.get('product_id'):
                            product_product = self.env['product.product'].sudo()
                            prod_dom = [('shopify_instance_id', '=', marketplace_instance_id.id)]
                            # if line['sku'] is not None and line['sku'] != '':
                                # prod_dom += [('default_code', '=', str(line['sku']))]
                                # prod_dom += ['|']
                            prod_dom += [('shopify_id', '=', str(line['product_id']))]
                            prod_rec = self.env['shopify.product.mappings'].search(prod_dom, limit=1).product_id

                        if not prod_rec and marketplace_instance_id.auto_create_product and line.get('product_id'):
                            _logger.info("# Need to create a new product")
                            sp_product_list = self.env['products.fetch.wizard'].shopify_fetch_products_to_odoo({
                                'product_id': line.get('product_id'),
                                'marketplace_instance_id': marketplace_instance_id,
                                'fetch_o_product': 'true',
                                'mappings_only': marketplace_instance_id.is_sku,
                            })
                            # prod_rec = self.env['product.product'].sudo().search(prod_dom, limit=1)
                            prod_rec = self.env['shopify.product.mappings'].search(prod_dom, limit=1).product_id

                        tip_product = False
                        if not line.get('variant_id') and not line.get('product_id'):
                            if line.get('name') == "Tip" or line.get('title') == "Tip":
                                tip_product = True
                                prod_rec = self.env.ref('syncoria_shopify.shopify_tip')

                        if not prod_rec:
                            prod_rec_variant_id = line.get('variant_id') or line.get('product_id') or ''
                            log_msg = """Product not found for Shopify ID-{}, Name: {}, SKU: {}""".format(
                                prod_rec_variant_id, line.get('name'), line.get('sku'))
                            error_msg_body += '\n' + log_msg

                        product_missing = True if not prod_rec else product_missing
                        temp = {}
                        product_tax = False
                        if marketplace_instance_id.apply_tax:
                            product_tax = self._shopify_get_taxnames(line['tax_lines'])
                            product_tax = list(filter(bool, product_tax))
                        _logger.info("prod_rec===>>>>>" + str(prod_rec))
                        _logger.warning("Order Creation Failed for Shopify Order Id: %s" % (
                            i['id'])) if product_missing else None
                        if product_missing:
                            log_msg = "Product is missing for Feed Order-{}".format(self)
                            error_msg_body += '\n' + log_msg
                            _logger.info(log_msg)
                            rec.message_post(body=log_msg)
                            self.write({'state': 'failed'})
                            return msg_body, error_msg_body

                        if not order_vals['partner_id']:
                            log_msg = "Unable to Create Order %s. Reason: Partner ID Missing" % (
                                order_vals['shopify_id'])
                            error_msg_body += '\n' + log_msg
                            _logger.info(log_msg)
                            rec.message_post(body=error_msg_body)
                            self.write({'state': 'failed'})
                            return msg_body, error_msg_body

                        if line and line.get('quantity') > 0 and not tip_product:
                            #####################################################################################
                            # TO DO: Compute Price from Pricelist
                            #####################################################################################
                            price_unit = float(line.get('price_set', {}).get('shop_money', {}).get('amount'))
                            pricelist_currency = marketplace_instance_id.pricelist_id.currency_id.name
                            shop_currency_code = line.get('price_set', {}).get('shop_money', {}).get('currency_code')
                            pre_currency_code = line.get('price_set', {}).get('presentment_money', {}).get('currency_code')
                            if pricelist_currency and shop_currency_code:
                                _logger.info(
                                    "\npricelist_currency-{}\nshop_currency_code-{}\npre_currency_code-{}".format(
                                        pricelist_currency, shop_currency_code, pre_currency_code))
                                if pricelist_currency == shop_currency_code:
                                    _logger.info("Shop and Pricelist Currency Matches")
                                else:
                                    _logger.info("Shop and Pricelist Currency Not Matching")
                                    price_unit = self.compute_price_unit(prod_rec, price_unit)

                            _logger.info("price_unit-{}".format(price_unit))
                            #####################################################################################
                            _logger.info("prod_rec-{}".format(prod_rec))
                            if prod_rec:
                                temp = {
                                    'product_id': prod_rec.id,
                                    'product_uom_qty': line['quantity'],
                                    'price_unit': price_unit,
                                    'tax_ids': [(6, 0, product_tax)] if product_tax else False,
                                    'name': str(prod_rec.name),
                                }

                                if marketplace_instance_id.user_id:
                                    temp['salesman_id'] = marketplace_instance_id.user_id.id

                                temp['shopify_id'] = line.get('id')

                                """ Properties added in description(Ex: Grind Type)"""
                                if line.get("properties"):
                                    temp["name"]=f"{str(prod_rec.name)}\n" + '\n'.join(map(lambda item: f"{item['name']}: {item['value']}", line.get("properties")))


                                "====================================================="

                                """ LEGACY """
                                discount = 0
                                if line.get("discount_allocations"):
                                    for da in line.get("discount_allocations"):
                                        discount += float(da.get('amount'))
                                    disc_per = (float(
                                        discount) / (float(line.get("price")) * line.get("quantity")) * 100)
                                    temp['discount'] = disc_per

                                # if line.get("discount_allocations"):
                                #     line_coupon_ids = []
                                #     for discount_applied in line.get("discount_allocations"):
                                #         code = discount_applied.get('code')
                                #         discount_name = self.env['shopify.coupon'].sudo().search(
                                #             [('name', '=', code)])
                                #         if not discount_name:
                                #             discount_name = self.env['shopify.coupon'].create(
                                #                 {"name": code})
                                #         if discount_name:
                                #             line_coupon_ids.append((4, discount_name.id))
                                #     temp['line_coupon_ids'] = line_coupon_ids
                                order_line.append((0, 0, temp))

                        if tip_product:
                            order_line.append((0, 0, {
                                'product_id': prod_rec.id,
                                'product_uom_qty': line['quantity'],
                                'price_unit': line['price'],
                                'name': line['name'] or line['title'],
                            }))

                    # for discount in i.get('discount_codes'):
                    #     discount_code = discount.get('code')
                    #     discount_amount = discount.get('amount')
                    #     product_discount_id = self.env.ref('syncoria_shopify.shopify_discount')
                    #     order_line.append((0, 0, {'name': discount_code, 'product_uom_qty': 1,
                    #                               'price_unit': -float(discount_amount), 'product_id': product_discount_id.id}))

                    # Set Shipping Address
                    shipping = False

                    order_vals['order_line'] = order_line
                    order_vals = self._get_delivery_line(i, order_vals, marketplace_instance_id, product_tax)
                    # Other Values

                    order_vals['shopify_status'] = i.get('status', '')
                    order_vals['shopify_order_date'] = i.get('created_at').split(
                        "T")[0] + " " + i.get('created_at').split("T")[1][:8]
                    # order_vals['shopify_carrier_service'] = i.get('')
                    order_vals['shopify_has_delivery'] = i.get('')
                    order_vals['shopify_browser_ip'] = i.get('browser_ip')
                    order_vals['shopify_buyer_accepts_marketing'] = i.get('buyer_accepts_marketing')
                    order_vals['shopify_cancel_reason'] = i.get('cancel_reason')
                    if i.get('cancelled_at'):
                        order_vals['shopify_cancelled_at'] = i.get('cancelled_at').split(
                            "T")[0] + " " + i.get('cancelled_at').split("T")[1][:8]
                    order_vals['shopify_cart_token'] = i.get('cart_token')
                    order_vals['shopify_checkout_token'] = i.get('checkout_token')

                    currency = self.env['res.currency'].search([('name', '=', i.get('currency'))])
                    if currency:
                        order_vals['shopify_currency'] = currency.id
                    order_vals['shopify_financial_status'] = i.get(
                        'financial_status')
                    order_vals['shopify_fulfillment_status'] = i.get(
                        'fulfillment_status')

                    tags = i.get('tags').split(",")
                    try:
                        tag_ids = []
                        for tag in tags:
                            tag_id = self.env['crm.tag'].search([('name', '=', tag)])
                            if not tag_id and tag != "":
                                tag_id = self.env['crm.tag'].create({"name": tag, "color": 1})
                            if tag_id:
                                tag_ids.append((4, tag_id.id))
                        order_vals['tag_ids'] = tag_ids
                    except Exception as e:
                        _logger.warning(e)

                    """ COUPONS """
                    if 'discount_codes' in i:
                        coupon_ids = []
                        for coupon in i['discount_codes']:
                            coupon_name = self.env['shopify.coupon'].sudo().search([('name', '=', coupon.get('code'))])
                            if not coupon_name:
                                coupon_name = self.env['shopify.coupon'].create({"name": coupon.get('code')})
                            if coupon_name:
                                coupon_ids.append((4, coupon_name.id))
                        if coupon_ids:
                            order_vals['coupon_ids'] = coupon_ids

                    if 'message_follower_ids' in order_vals:
                        order_vals.pop('message_follower_ids')
                    order_vals['name'] = self.env['ir.sequence'].next_by_code('sale.order')

                    order_id = False
                    if order_vals.get('order_line'):


                        if not product_missing and order_vals['partner_id']:
                            # Update Transaction Fees and create a Sale Order Line
                            # order_vals = self.update_transaction_fee_line(i, order_vals)
                            # order_vals['shopify_sale_channel'] = i.get('source_name')
                            order_id = self.env['sale.order'].with_user(SUPERUSER_ID).with_context({'is_shopify_order': True}).create(order_vals)
                            if order_id.shopify_financial_status == 'partially_refunded':
                                error_shopify_tag_id = self.env.ref("syncoria_shopify.partially_refunded", raise_if_not_found=False)
                                if error_shopify_tag_id:
                                    order_id.shopify_err_tag_ids |= error_shopify_tag_id
                            log_msg = "Sale Order Created-{} for Feed Order-{}".format(order_id, self)
                            msg_body += '\n' + log_msg
                            _logger.info(log_msg)

                            if order_id:
                                self.write({
                                    'state': 'processed',
                                    'sale_id': order_id.id,
                                })
                                all_shopify_orders += order_id

                                if i.get('confirmed'):
                                    order_id.with_context({'date_order': order_vals['date_order'], 'is_shopify_order': True}).action_confirm()

                                # if i.get("cancel_reason") and i.get('cancelled_at'):
                                #     order_id.action_cancel()
                            order_id.env.cr.commit()
                else:
                    current_order_id = order_exists

                    # if i.get("cancel_reason") and i.get('cancelled_at'):
                    #     current_order_id.action_cancel()
                    all_shopify_orders += current_order_id

                    shopify_financial_status = i.get('financial_status')
                    if current_order_id.shopify_financial_status != shopify_financial_status:
                        current_order_id.shopify_financial_status = shopify_financial_status
                    if shopify_financial_status == 'partially_refunded':
                        error_shopify_tag_id = self.env.ref("syncoria_shopify.partially_refunded", raise_if_not_found=False)
                        if error_shopify_tag_id:
                            current_order_id.shopify_err_tag_ids |= error_shopify_tag_id

                    tags = i.get('tags').split(",")
                    try:
                        tag_ids = []
                        for tag in tags:
                            tag_id = self.env['crm.tag'].search([('name', '=', tag)], limit=1)
                            if not tag_id and tag != "":
                                tag_id = self.env['crm.tag'].create({"name": tag, "color": 1})
                            if tag_id:
                                tag_ids.append(tag_id.id)
                        if tag_ids:
                            current_order_id.tag_ids = tag_ids
                        else:
                            current_order_id.tag_ids.unlink()

                    except Exception as e:
                        _logger.warning(e)

                    log_msg = """Shopify Order exists for Feed Order {}, Sale Order-{}""".format(self, order_exists.name)
                    msg_body += '\n' + log_msg
                    _logger.info(log_msg)
                    if current_order_id:
                        self.write({
                            'state': 'processed',
                            'sale_id': current_order_id.id,
                        })

                log_msg = """Shopify Process Feed Order finished for {}, Shopify ID-{}""".format(rec.name, rec.shopify_id)
                msg_body += '\n' + log_msg
                _logger.info(log_msg)
                rec.message_post(body=msg_body)
            except UserError as e:
                msg = "Exception occurred in process feed order{}".format(e.args)
                raise ValidationError(msg)
            except Exception as e:
                msg = "Exception occurred in process feed order{}".format(e.args)
                error_msg_body += '\n' + msg
                rec.message_post(body=msg)
                rec.write({'state': 'failed'})
                return msg, error_msg_body
                # raise ValidationError(e)

        ################################################################
        ###########Fetch the Payments and Refund for the Orders#########
        ################################################################
        for shopify_order in all_shopify_orders:
            shopify_order.fetch_shopify_payments()
            shopify_order.fetch_shopify_refunds()
            shopify_order.get_order_fullfillments()

            if shopify_order and shopify_order.state not in ['draft'] and marketplace_instance_id.auto_create_invoice:
                _logger.info("==========> Process Invoice Start")
                shopify_order.process_shopify_invoice()
                _logger.info("==========> Process Invoice Payment Start")
                shopify_order.shopify_invoice_register_payments()
                if shopify_order.shopify_financial_status in ['refunded', 'partially_refunded']:
                    _logger.info("==========> Process Credit Note Start")
                    shopify_order.process_shopify_credit_note()
                    _logger.info("==========> Process Credit Note Payment Start")
                    shopify_order.shopify_credit_note_register_payments()
            if shopify_order and shopify_order.state not in ['draft'] and marketplace_instance_id.auto_create_fulfilment:
                _logger.info("==========> Process Fullfilment Start")
                shopify_order.process_shopify_fulfilment()
                # self.process_shopify_return_fulfillment(shopify_order)

            self.env.cr.commit()

        return msg_body, error_msg_body
            
    def process_shopify_return_fulfillment(self, shopify_order):
        """
            Processs Shopify Return Fulfillment
        """
        shopify_feed_orders = self.env['shopify.feed.orders']
        feed_order = shopify_feed_orders.search([('shopify_id', '=', shopify_order.shopify_id)], limit=1)

        if feed_order:
            order_data = json.loads(feed_order.order_data)
            # print("order_data ===>>> {}".format(order_data))

            if order_data.get('financial_status') in ['partially_refunded', 'refunded']:
                financial_status = order_data.get('financial_status')
                _logger.info("financial_status ===>>> {}".format(financial_status))

                stock_picking = self.env['stock.picking']
                stock_return_picking = self.env['stock.return.picking']
                stock_return_picking_line = self.env['stock.return.picking.line']
                product_product = self.env['product.product']
                delivery_picking_id = stock_picking.search([('origin', '=', shopify_order.name)])


                domain = [('sale_id', '=', shopify_order.id)]
                domain += [('picking_type_code', '=', 'incoming')]
                return_picking_id = self.env['stock.picking'].search(domain)

                if len(delivery_picking_id) == 1:
                    if not delivery_picking_id.is_return_picking and delivery_picking_id.state == 'done':
                        if order_data.get('refunds'):
                            for refund in order_data.get('refunds'):
                                _logger.info("refund ===>>> {}".format(refund.get('id')))

                                product_return_moves = []
                                for refund_line in refund.get('refund_line_items'):
                                    line_item = refund_line['line_item']
                                    product_id = self.env['shopify.product.mappings'].search([('shopify_id', '=', line_item['variant_id'])], limit=1).product_id
                                    # product_id = product_product.search([('shopify_id', '=', line_item['variant_id'])])
                                    order_line = shopify_order.order_line.filtered(lambda l: l.product_id.id == product_id.id)

                                    # _logger.info("refund_line ===>>> {}".format(refund_line))
                                    # _logger.info("line_item ===>>> {}".format(line_item))
                                    # _logger.info("product_id ===>>> {}".format(product_id))
                                    # _logger.info("order_line ===>>> {}".format(order_line))

                                    if product_id and line_item['quantity'] > 0 and order_line.product_uom_qty - order_line.qty_delivered == 0:
                                        product_uom_qty = sum(return_picking_id.move_ids.filtered(lambda l: l.product_id.id == product_id.id).mapped('product_uom_qty'))
                                        move_id = delivery_picking_id.move_line_ids.filtered(lambda l: l.product_id.id == product_id.id)
                                        
                                        if line_item['quantity'] > product_uom_qty and move_id:
                                            product_return_moves += [(0, 0, {
                                                'move_id' : move_id.id,
                                                'product_id' : product_id.id,
                                                'quantity' : line_item['quantity'],
                                                'to_refund' : True,
                                                'uom_id' : product_id.uom_id.id,
                                            })]

                                if product_return_moves:
                                    _logger.info("product_return_moves ===>>> {}".format(product_return_moves))
                                    stock_return_picking_id = self.env['stock.return.picking'].with_context(
                                        active_ids=delivery_picking_id.ids, 
                                        active_id=delivery_picking_id.id,
                                        active_model='stock.picking',
                                        # company_id=delivery_picking_id.company_id.id,
                                        # location_id=delivery_picking_id.location_id.id,
                                        # original_location_id=delivery_picking_id.location_id.id,
                                        # parent_location_id=delivery_picking_id.location_id.location_id.id,
                                        # picking_id=delivery_picking_id.id,
                                    ).create({
                                        'company_id': delivery_picking_id.company_id.id,
                                        'location_id': delivery_picking_id.location_id.id,
                                        'original_location_id': delivery_picking_id.location_id.id,
                                        'parent_location_id': delivery_picking_id.location_id.location_id.id,
                                        'picking_id': delivery_picking_id.id,
                                    })

                                    if stock_return_picking_id:
                                        self.env.cr.commit()
                                    
                                    if stock_return_picking_id and not stock_return_picking_id.location_id:
                                        stock_return_picking_id.location_id = delivery_picking_id.location_id.id
                                    
                                    srp_line = self.env['stock.return.picking.line']
                                    if product_id and line_item['quantity'] > 0 and order_line.product_uom_qty - order_line.qty_delivered == 0:
                                        move_id = delivery_picking_id.move_line_ids.filtered(lambda l: l.product_id.id == product_id.id)
                                        
                                        srp_line += self.env['stock.return.picking.line'].create({
                                            'move_id' : move_id.id,
                                            'product_id' : product_id.id,
                                            'quantity' : line_item['quantity'],
                                            'to_refund' : True,
                                            'uom_id' : product_id.uom_id.id,
                                            'wizard_id' : stock_return_picking_id.id,
                                        })
                                    if srp_line:
                                        _logger.info("stock_return_picking_id ===>>> {}".format(stock_return_picking_id))
                                        stock_return_picking_id.product_return_moves = srp_line.ids

                                    new_picking_id, pick_type_id = stock_return_picking_id._create_returns()

                                    if new_picking_id:
                                        picking_id = self.env['stock.picking'].browse(new_picking_id)


                                        if picking_id and picking_id.sale_id:
                                            if picking_id.sale_id.id != shopify_order.id:
                                                picking_id.sale_id = shopify_order.id

                                        if picking_id and not picking_id.sale_id:
                                            picking_id.sale_id = shopify_order.id




                                        if picking_id and picking_id.state != 'done':
                                            try:
                                                picking_id.action_confirm()
                                                picking_id.action_assign()
                                                validate_picking = picking_id.button_validate()
                                            except Exception as e:
                                                _logger.info("Exception ===>>> {}".format(e.args))

                                            # if type(validate_picking) == dict and validate_picking.get('res_model') == 'stock.backorder.confirmation':
                                            #     self.env['stock.backorder.confirmation'].with_context(validate_picking.get('context')).process()
                                    
                                    
                                    _logger.info("new_picking_id ===>>> {}".format(new_picking_id))
                                    _logger.info("pick_type_id ===>>> {}".format(pick_type_id))

                if order_data.get('financial_status') in ['refunded'] and order_data.get('cancel_reason'):
                    if shopify_order.state != 'cancel':
                        shopify_order.action_cancel()
                        shopify_order.write({'shopify_cancel_reason': order_data.get('cancel_reason')})

    def update_transaction_fee_line(self, i, order_vals):
        if i.get('id'):
            shopify_id = i.get('id')
            marketplace_instance_id = self.instance_id
            if not getattr(marketplace_instance_id, "use_graphql", False):
                raise ValidationError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")

            # Shopify REST transactions include `receipt.metadata` (used for fee breakdown) but GraphQL doesn't expose it.
            # To remain GraphQL-only, we skip transaction-fee line creation here.
            _logger.info(
                "Skipping transaction fee line for Shopify order %s (GraphQL-only; receipt.metadata unavailable).",
                shopify_id,
            )



        return order_vals

    def _get_delivery_line(self, i, order_vals, marketplace_instance_id, taxes=False):
        ProductObj = self.env['product.product'].sudo()
        service = self.env.ref('syncoria_shopify.shopify_shipping')
        if i.get('shipping_lines'):
            # Find shipping service from Shopify Order\
            for ship_line in i.get('shipping_lines'):
                domain = [('default_code', '=', ship_line['code'])]
                service = ProductObj.search(domain, limit=1) if not service else service
                if marketplace_instance_id.delivery_product_id:
                    service = marketplace_instance_id.delivery_product_id
                # if len(service) == 0:
                #     ship_values = self._shopify_get_ship(
                #         ship_line, marketplace_instance_id)
                #     service = ProductObj.create(ship_values)

                shipping_name = ship_line.get('title')
                product_name = ship_line.get('title')
                _logger.info(ship_line)
                shipping_mapping = marketplace_instance_id.shopify_shipping_method_mappings.filtered(lambda s: s.name == ship_line.get('title'))
                order_vals['shopify_carrier_service'] = ship_line.get('title')
                if shipping_mapping:
                    service = shipping_mapping.product_id
                    order_vals['carrier_id'] = shipping_mapping.carrier_id.id
                ship_tax = []
                if ship_line.get('tax_lines') and len(ship_line.get('tax_lines')) > 0 and marketplace_instance_id.apply_tax:
                    ship_tax = self._shopify_get_taxnames(ship_line.get('tax_lines'))
                    # disc_per = 0
                    # if ship_line.get("discounted_price") != ship_line.get("price"):
                    #     if float(line.get("discounted_price")) != 0:
                    #         discount = float(
                    #             line.get("price")) - float(line.get("discounted_price"))
                    #         disc_per = (
                    #             discount/line.get("price")) * 100
                if taxes and not ship_tax:
                    ship_tax = taxes
                #####################################################################################
                # TO DO: Compute Price from Pricelist
                delivery_price = ship_line.get('price')
                pricelist_currency = marketplace_instance_id.pricelist_id.currency_id.name
                shop_currency_code = ship_line.get('price_set', {}).get('shop_money', {}).get('currency_code')
                pre_currency_code = ship_line.get('price_set', {}).get('presentment_money', {}).get('currency_code')
                if pricelist_currency and shop_currency_code:
                    _logger.info("\npricelist_currency-{}\nshop_currency_code-{}\npre_currency_code-{}".format(
                        pricelist_currency, shop_currency_code, pre_currency_code))
                    if pricelist_currency == shop_currency_code:
                        _logger.info("Shop and Pricelist Currency Matches")
                    else:
                        _logger.info("Shop and Pricelist Currency Not Matching")
                        delivery_price = self.compute_price_unit(service, delivery_price)
                        # Convert Price to Pricelist Currency
                        delivery_price = marketplace_instance_id.pricelist_id.currency_id.rate * float(delivery_price)

                _logger.info("Shipping Pirce Unit-{}".format(delivery_price))
                #####################################################################################
                temp = {
                    'product_id': service.id,
                    'name': shipping_name,
                    'is_delivery': True,
                    'product_uom_qty': 1,
                    'price_unit': delivery_price,
                    # 'discount': disc_per,
                    'tax_ids': [(6, 0, ship_tax)],
                }
                order_vals['order_line'].append((0, 0, temp))

        else:
            temp = {
                'product_id': service.id,
                'product_uom_qty': 1,
                'price_unit': 0.00,
                'tax_ids': [(6, 0, [])],
            }
            order_vals['order_line'].append((0, 0, temp))
        return order_vals

    def process_discount_codes(self, sp_order, order_vals):
        VariantObj = self.env['product.product'].sudo()
        total_discount = 0
        # total_discount = -float(sp_order.get('current_total_discounts')
        #                         ) if sp_order.get('current_total_discounts') else 0
        if total_discount == 0:
            if len(sp_order.get('discount_codes')) > 0:
                _logger.info("discount_codes===>>>" +
                             str(sp_order.get('discount_codes')))
                for disc in sp_order.get('discount_codes'):
                    if disc['type'] != 'percentage':
                        total_discount -= float(disc.get('amount'))

        service = self.env.ref('syncoria_shopify.shopify_discount')
        service = VariantObj.search(
            [('name', '=', 'Discount')], limit=1) if not service else service
        if service:
            #####################################################################################
            #TO DO: Compute Price from Pricelist
            #####################################################################################
            temp = {
                'product_id': service.id,
                'product_uom_qty': 1,
                'price_unit': total_discount,
                'tax_ids': [(6, 0, [])],
            }
            print("temp--->", temp)
            order_vals['order_line'].append((0, 0, temp))
        return order_vals


    def _shopify_get_ship(self, ship_line, ma_ins_id):
        ship_value = {}
        ship_value['name'] = ship_line.get('title')
        ship_value['sale_ok'] = False
        ship_value['purchase_ok'] = False
        ship_value['type'] = 'service'
        ship_value['default_code'] = ship_line.get('code')
        categ_id = self.env['product.category'].sudo().search(
            [('name', '=', 'Deliveries')], limit=1)
        ship_value['categ_id'] = categ_id.id
        ship_value['company_id'] = ma_ins_id.company_id.id
        ship_value['responsible_id'] = ma_ins_id.user_id.id
        return ship_value

    def _shopify_get_taxnames(self, tax_lines):
        tax_names = []
        Tax = self.env['account.tax']
        for tax_id in tax_lines:
            tax_title = f"{tax_id['title']} {tax_id['rate'] * 100}%"

            # Try to use Odoo existing taxes
            tax_ob = Tax.sudo().search([
                "&",
                ("shopify_tax_title_contains", "ilike", tax_id['title']),
                ("shopify_tax_title_contains", "ilike", int(tax_id['rate'] * 100)),
            ], limit=1)

            if not tax_ob:
                search_domain = [
                    ('shopify_tax_title', '=', tax_title),
                    ('amount', '=', tax_id['rate'] * 100),
                    ('type_tax_use', '=', 'sale'),
                    ('marketplace_type', '=', 'shopify'),
                    ('company_id','=',self.instance_id.company_id.id)
                ]
                tax_ob = Tax.sudo().search(search_domain, limit=1)
            if not tax_ob:
                tax_ob = Tax.sudo().create({
                    'name': tax_title,
                    'shopify_tax_title': tax_title,
                    'amount': tax_id['rate'] * 100,
                    'type_tax_use': 'sale',
                    'marketplace_instance_id': self.instance_id.id,
                    'company_id': self.instance_id.company_id.id,
                    'tax_group_id': self.instance_id.tax_group_id.id
                })

            tax_names.append(tax_ob.id)
        return tax_names

    # def _match_or_create_address(self, partner, checkout, contact_type):
    #     Partner = self.env['res.partner']
    #     street = checkout.get('address1')
    #     street2 = checkout.get('address2')
    #     azip = checkout.get('zip')
    #     if partner:
    #         delivery = partner.child_ids.filtered(lambda c: (c.street == street or c.street2 == street2 or c.zip == azip) and c.type == contact_type)

    #         country_domain = [('name', '=', checkout.get(
    #             'country'))] if checkout.get('country') else []

    #         country_id = self.env['res.country'].sudo().search(
    #             country_domain, limit=1)

    #         state_domain = [('country_id', '=', country_id.id)
    #                          ] if country_id else []
    #         state_domain += [('name', '=', checkout.get('province'))
    #                           ] if checkout.get('province') else state_domain
    #         state_id = self.env['res.country.state'].sudo().search(
    #             state_domain, limit=1)

    #         if not delivery:
    #             delivery = Partner.sudo().with_context(tracking_disable=True).create({
    #                 'name': checkout.get('name', None),
    #                 'street': street,
    #                 'street2': street2,
    #                 'zip': azip,
    #                 'country_id': country_id.id,
    #                 'state_id': state_id.id,
    #                 'city': checkout.get('city', None),
    #                 'parent_id': partner.id,
    #                 'property_account_receivable_id' : partner.property_account_receivable_id.id,
    #                 'property_account_payable_id' : partner.property_account_payable_id.id,
    #                 'type': contact_type,
    #                 'phone': checkout.get('phone'),
    #             })
    #         return delivery[0]
    #     else:
    #         return False

    def _process_customer_addresses(self, partner_id, item):
        vals = {}
        if type(item['addresses']) == dict:
            if item.get('addresses'):
                for address in item.get('addresses'):
                    if address.get('default') and partner_id.type == 'invoice':
                        partner_id.write({
                            'shopify_default': True,
                            'shopify_add_id': address.get('id'),
                        })
                    if address.get('default') == False:
                        domain = [('shopify_add_id', '=', address.get('id'))]
                        res_partner = self.env['res.partner']
                        part_id = res_partner.sudo().search(domain, limit=1)
                        if not part_id:
                            add_vals = get_address_vals(self.env, address)
                            add_vals['type'] = 'other'
                            add_vals['parent_id'] = partner_id.id
                            add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                            add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id
                            try:
                                with self.env.cr.savepoint():
                                    res_partner.sudo().create(add_vals)
                            except Exception as e:
                                _logger.warning("Skip child address create (shopify_add_id=%s): %s", address.get('id'), e)
        elif type(item.get('addresses')) == list:
            for address in item['addresses']:
                if address.get('default') and partner_id.type == 'invoice':
                    partner_id.write({
                        'shopify_default': True,
                        'shopify_add_id': address.get('id'),
                    })
                if address.get('default') == False:
                    domain = [('shopify_add_id', '=', address.get('id'))]
                    res_partner = self.env['res.partner']
                    part_id = res_partner.sudo().search(domain, limit=1)
                    if not part_id:
                        add_vals = get_address_vals(self.env, address)
                        add_vals['type']='other'
                        add_vals['parent_id'] = partner_id.id
                        add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                        add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id
                        try:
                            with self.env.cr.savepoint():
                                res_partner.sudo().create(add_vals)
                        except Exception as e:
                            _logger.warning("Skip child address create (shopify_add_id=%s): %s", address.get('id'), e)

        return vals

    def get_sale_order_vals(self, marketplace_instance_id, customer_id, i):
        order_vals = {}
        if marketplace_instance_id:
            order_vals['warehouse_id'] = marketplace_instance_id.warehouse_id.id if marketplace_instance_id.warehouse_id else None
            order_vals['company_id'] = marketplace_instance_id.company_id.id or self.env.company.id
            order_vals['user_id'] = marketplace_instance_id.user_id.id if marketplace_instance_id.user_id else None
            order_vals['fiscal_position_id'] = marketplace_instance_id.fiscal_position_id.id or None
            order_vals['pricelist_id'] = marketplace_instance_id.pricelist_id.id if marketplace_instance_id.pricelist_id else None
            order_vals['payment_term_id'] = marketplace_instance_id.payment_term_id.id if marketplace_instance_id.payment_term_id else None
            order_vals['team_id'] = marketplace_instance_id.sales_team_id.id if marketplace_instance_id.sales_team_id else None
            order_vals['marketplace_instance_id'] = marketplace_instance_id.id
            order_vals['shopify_id'] = str(i['id'])
            order_vals['partner_id'] = customer_id
            order_vals['shopify_status'] = i.get('confirmed')
            order_vals['shopify_order'] = i.get('name')
            order_vals['shopify_financial_status'] = i.get('financial_status')
            order_vals['shopify_fulfillment_status'] = i.get('fulfillment_status')
            order_vals['date_order'] = i.get('created_at')
            if i.get('created_at'):
                # order_vals['date_order'] = i.get('created_at').split(
                #     "T")[0] + " " + i.get('created_at').split("T")[1].split("+")[0].split('-')[0]
                dt = datetime.fromisoformat(i.get('created_at'))
                dt_utc_naive = dt.astimezone(timezone.utc).replace(tzinfo=None)
                order_vals["date_order"] = fields.Datetime.to_string(dt_utc_naive)
            # order_vals['analytic_account_id'] = marketplace_instance_id.analytic_account_id.id if marketplace_instance_id.analytic_account_id else None
        return order_vals

# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _

import pprint
import json

from odoo import exceptions
from ..shopify.utils import *
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_latitude = fields.Char(
        string='Latitude',
    )
    shopify_longitude = fields.Char(
        string='Longitude',
    )
    shopify_id = fields.Char(string="Shopify ID",
                             store=True
                             # readonly=True,
                             )
    shopify_add_id = fields.Char(string="Address id",
                             store=True,
                             readonly=True,
                             )
    shopify_warehouse_id = fields.Char(string="Shopify Warehouse ID",
                                 store=True,
                                 readonly=True,
                                 )
    shopify_warehouse_active = fields.Boolean(string="Shopify Warehouse Active")
    shopify_accepts_marketing = fields.Boolean(
        string='Email Marketing',
        default=False,
    )

    shopify_last_order_id = fields.Char(string="Last Order Id", readonly=True)
    shopify_last_order_name = fields.Char(string="Last Order Name", readonly=True)
    marketing_opt_in_level = fields.Selection(
        string='field_name',
        selection=[('single_opt_in', 'single_opt_in'), ('confirmed_opt_in', 'confirmed_opt_in'),('unknown','unknown')],
        readonly=True,
    )
    multipass_identifier = fields.Char(string="Multi Pass Identifier", readonly=True)
    orders_count = fields.Integer(
        string='Orders Count',
    )
    shopify_state = fields.Selection(
        string='Shopify Status',
        selection=[('disabled', 'Disabled'), ('invited', 'Invited'),('enabled','Enabled'),('declined','Declined')],
    )

    shopify_tax_settings = fields.One2many(
        string='Tax Settings',
        comodel_name='shopify.tax.settings',
        inverse_name='partner_id',
        readonly=True,
    )
    # Tags---->category_id
    shopify_tax_exempt = fields.Boolean(
        string='Tax Exempt',
        default=False,
        readonly=True,
    )
    shopify_tax_exemptions_ids = fields.One2many(
        string='Shopify Tax Exemptions',
        comodel_name='shopify.tax.exemptions',
        inverse_name='partner_id',
        readonly=True,
    )

    shopify_total_spent = fields.Monetary(string="Total Spent", readonly=True)
    shopify_verified_email = fields.Boolean(
        string='Verified Email',
        default=False,
        readonly=True,
    )
    shopify_default = fields.Boolean(default=False)
    shopify_company_name = fields.Char(string="Shopify Contact Company Name")

    def create_shopify_customer(self):
        """
            Button Name: Create Shopify Customer
            Action: Creates a Customer in Shopify
        """
        data = {}
        response = shopify_cus_req(self, data, 'search')
        response = json.loads(response)
        if len(response.get('customers')) == 0:
            data = shopify_customer_values(self)
            customer = shopify_cus_req(self, data, 'create')
            customer = json.loads(customer)

            _logger.info("\customer created===>>>\n", customer)
            if customer.get('errors'):
                raise exceptions.UserError(_(str(customer.get('errors'))))
            elif customer.get('customer', {}).get("id"):
                if not self.shopify_id:
                    self.write(
                        {'shopify_id': customer.get("customer", {}).get("id")})

                body = _("Customer Create Successful in Shopify with Shopify Id- %s " +
                         str(customer.get("customer").get("id")))
                _logger.info(body)

                if len(customer.get('customer', {}).get("addresses")) == 0:
                    address = self._create_shopify_address()
                    _logger.info('address------>>>>>>>>>>>>>>>>')
                    _logger.info(address)
                self.message_post(body=body)
        else:
            raise exceptions.UserError(
                _("Custmer with same Email Address-`%s` already exists on Shopify", self.email))

    def update_shopify_customer(self):
        """
            Button Name: Update Shopify Customer
            Action: Updates a Customer in Shopify
        """
        data = shopify_customer_values(self)
        customer = shopify_cus_req(self, data, 'update')
        customer = json.loads(customer)
        # _logger.info("Updated Customer Response===>>>" + str(customer))
        if customer.get('errors'):
            raise exceptions.UserError(_(str(customer.get('errors'))))
        elif customer.get('customer', {}).get("id"):
            customer_id = customer.get("customer").get("id")
            body = "Customer Update Successful for Shopify Id- %s " %(customer_id)
            if customer.get('customer',{}).get('addresses'):
                addresses = customer.get('customer',{}).get('addresses')
                if len(addresses) == 0:
                    data = self._create_shopify_address()
                    _logger.info('data------>>>>>' + str(data))
                    address = shopify_cus_req(self, data, 'create')
                    if address.get('id'):
                        body += """,\nCustomer Address Create Successful for Shopify Id: %s, Address Id: %s""" %(self.shopify_id, self.shopify_add_id)

                if len(addresses) == 1:
                    address_id = addresses[0].get('id')
                    self.write({'shopify_add_id': address_id})
                    body += """,\nCustomer Address Update Successful for Shopify Id: %s, Address Id: %s""" %(self.shopify_id, self.shopify_add_id)

                if len(addresses) > 1:
                    msg = """Check the addresses , if not matching ,update on Shopify"""
                    _logger.info(msg)

                body = self._process_child_ids(customer, body)
                

            _logger.info(body)
            _logger.info("Length of Address: " + str(len(customer.get('customer',{}).get('addresses'))))
            self.message_post(body=body)

    def _process_child_ids(self, customer, body):
        body =""
        # Process for Child Ids
        if len(self.child_ids) > 0:
            for child in self.child_ids:
                action = 'create' if not child.shopify_add_id else 'update'
                data = shopify_address_values(child)
                address = shopify_add_req(self, data, action)
                address = json.loads(address)
                if address.get('errors'):
                    body += "Address %s Error for %s:\n Errors:%s" %(action, str(self.shopify_add_id), str(address.get('errors')))
                    # raise exceptions.UserError(_(str(customer.get('errors'))))
                _logger.info(str(action) + 'address------>>>>>' + str(address))
                address_id = address.get('customer_address',{}).get('id') or address.get('id')
                _logger.info('address_id------>>>>>' + str(address_id))
                child.write({'shopify_add_id': address_id}) if not child.shopify_add_id else None
                body += """,\nCustomer Address """ + str(action) + """ Successful for Shopify Id: %s, Address Id: %s""" %(child.shopify_id, child.shopify_add_id) if address_id else ""
        return body



    def _create_shopify_address(self):
        address = {}
        delivery = None
        delivery = self if self.type == 'delivery' else None
        if not delivery and self.child_ids:
            for child in self.child_ids:
                if child.type == 'delivery':
                    delivery = child
        delivery = self if not delivery else delivery
        if delivery:
            data = shopify_address_values(delivery)
            address = shopify_add_req(self, data, 'create')
            _logger.info('address------>>>>>')
            _logger.info(address)
            if address.get('customer_address',{}).get('id'):
                address_id = address.get('customer_address',{}).get('id')
                _logger.info('address_id------>>>>>' + str(address_id))
                delivery.write({'shopify_add_id': address_id})


        return address

    ##############Should not delete from Shopify####################################
    # def unlink(self):
    #     for rec in self:
    #         if rec.marketplace_type == 'shopify' and rec.shopify_id != 0:
    #             response = shopify_add_req(rec,{},'delete')
    #             response = json.loads(response)
    #             _logger.info("response==>>>" +  str(response))
    #         result = super(ResPartner, rec).unlink()
    #     return result
    ##############Should not delete from Shopify####################################


class ShopifyTaxSettings(models.Model):
    _name = 'shopify.tax.settings'
    _description = 'Shopify Tax Settings'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('New'),
        copy=False
    )
    
    partner_id = fields.Many2one(
        string='partner',
        comodel_name='res.partner',
        ondelete='restrict',
    )

class ShopifyTaxExemptions(models.Model):
    _name = 'shopify.tax.exemptions'
    _description = 'Shopify TAx Exemptions'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('New'),
        copy=False
    )
    
    partner_id = fields.Many2one(
        string='partner',
        comodel_name='res.partner',
        ondelete='restrict',
    )
    


    


    
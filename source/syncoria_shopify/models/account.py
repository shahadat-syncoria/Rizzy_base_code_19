# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    shopify_id = fields.Char(string="Shopify Id")
    shopify_order = fields.Char(string="Shopify Order")


class AccountTax(models.Model):
    _inherit = 'account.tax'

    shopify_id = fields.Integer(string="Shopify Id")
    shopify_tax_title = fields.Char(string="Shopify Tax Title")
    shopify_tax_title_contains = fields.Char(string="Shopify Tax Title Contains")
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    shopify_id = fields.Char(string="Shopify Id")
    #Shopify Payment Info
    shopify_credit_card_bin = fields.Char('Shopify Credit Card BIN', copy=False)
    shopify_avs_result_code = fields.Char('Shopify Credit Card AVS', copy=False)
    shopify_cvv_result_code = fields.Char('Shopify Credit Card CVV', copy=False)
    shopify_credit_card_number = fields.Char('Shopify Credit Card Number', copy=False)
    shopify_credit_card_company = fields.Char('Shopify Credit Card Company', copy=False)
    shopify_payment_gateway_names = fields.Char('Shopify Payment Gateway Names', copy=False)
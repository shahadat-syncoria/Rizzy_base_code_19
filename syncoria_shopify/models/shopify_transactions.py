# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)



class ShopifyTransactions(models.Model):
    _name = 'shopify.transactions'
    _description = 'Shopify Transactions'
    _rec_name = 'name'


    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.transactions'))
    sale_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='set null',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='set null',
    )
    shopify_id = fields.Char(string='Shopify Id', readonly=True)
    shopify_order_id = fields.Char(string='Order Id', readonly=True)
    shopify_kind = fields.Char(string='Kind', readonly=True)
    shopify_gateway = fields.Char(string='Gateway', readonly=True)
    shopify_status = fields.Char(string='Status', readonly=True)
    shopify_message = fields.Char(string='Message', readonly=True)
    shopify_created_at = fields.Char(string='Created At', readonly=True)
    shopify_test = fields.Char(string='Test', readonly=True)
    shopify_authorization = fields.Char(string='Authorization', readonly=True)
    shopify_location_id = fields.Char(string='Location Id', readonly=True)
    shopify_user_id = fields.Char(string='User Id', readonly=True)
    shopify_parent_id = fields.Char(string='Parent Id', readonly=True)
    shopify_processed_at = fields.Char(string='Processed At', readonly=True)
    shopify_device_id = fields.Char(string='Device Id', readonly=True)
    shopify_error_code = fields.Char(string='Error Code', readonly=True)
    shopify_source_name = fields.Char(string='Source Name', readonly=True)
    shopify_receipt = fields.Char(string='Receipt', readonly=True)
    shopify_currency_exchange_adjustment = fields.Char(string='Currency Exchange Adjustment', readonly=True)
    shopify_amount = fields.Char(string='Amount', readonly=True)
    shopify_currency = fields.Char(string='Currency', readonly=True)
    shopify_admin_graphql_api_id = fields.Char(string='Admin Graphql Api Id', readonly=True)
    shopify_payment_details = fields.Char(string='Payment Details', readonly=True)
    shopify_payment_details_id = fields.Many2one(
        string='Payment Details IDs',
        comodel_name='shopify.payment.details',
        ondelete='restrict',
    )
    shopify_payment_receipt_id = fields.Many2one(
        string='Receipt IDs',
        comodel_name='shopify.payment.receipt',
        ondelete='restrict',
    )
    shopify_is_process = fields.Boolean(string="Is processed" ,default=False)
    shopify_exchange_rate = fields.Char(string='Exchange Rate', readonly=True)
    


class ShopifyPaymentDetails(models.Model):
    _name = 'shopify.payment.details'
    _description = 'Shopify Payment Details'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.payment.details'))
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    credit_card_bin = fields.Char(string='CC Bin', readonly=True)
    avs_result_code = fields.Char(string='AVS Result Code', readonly=True)
    cvv_result_code = fields.Char(string='CVV Result Code', readonly=True)
    credit_card_number = fields.Char(string='CC Number', readonly=True)
    credit_card_company = fields.Char(string='CC Company', readonly=True)
    credit_card_name = fields.Char(string='CC Name', readonly=True)
    credit_card_wallet = fields.Char(string='CC Wallet', readonly=True)
    credit_card_expiration_month = fields.Char(string='CC Expiration Month', readonly=True)
    credit_card_expiration_year = fields.Char(string='CC Expiration Year', readonly=True)
    


class ShopifyPaymentReceipt(models.Model):
    _name = 'shopify.payment.receipt'
    _description = 'Shopify Payment Receipt'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.payment.receipt'))

    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    testcase = fields.Char(string='CC Bin', readonly=True)
    authorization = fields.Char(string='AVS Result Code', readonly=True)
    paid_amount = fields.Char(readonly=True)
    
    shopify_receipt_metadata_ids = fields.One2many(
        string='Shopify Receipt Metadata',
        comodel_name='shopify.payment.receipt.metadata',
        inverse_name='receipt_id',
    )
    

class ShopifyPaymentReceiptMetadata(models.Model):
    _name = 'shopify.payment.receipt.metadata'
    _description = 'Shopify Payment Receipt Metadata'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('shopify.payment.receipt.metadata'),
        readonly=True)
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
        readonly=True)
    
    transaction_type = fields.Selection(
        selection=[('sale', 'Sale'), ('refund', 'Refund')],
        default='sale',
        readonly=True)
    #Metadata Fields: Start
    email = fields.Char(readonly=True)
    manual_entry = fields.Char(readonly=True)
    order_id = fields.Char(readonly=True)
    order_transaction_id = fields.Char(readonly=True, )
    payments_charge_id = fields.Char(readonly=True, )
    shop_id = fields.Char(readonly=True, )
    shop_name = fields.Char(readonly=True)
    transaction_fee_tax_amount = fields.Monetary()
    transaction_fee_total_amount = fields.Monetary()
    #Metadata Fields: End
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, )
    sale_id = fields.Many2one('sale.order', string='Sale Order', readonly=True, ondelete='set null',)
    receipt_id = fields.Many2one('shopify.payment.receipt', string='Receipt ID', readonly=True, )

    
    
    
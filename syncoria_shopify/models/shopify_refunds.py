# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)



class ShopifyRefunds(models.Model):
    _name = 'shopify.refunds'
    _description = 'Shopify Refunds'
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
    shopify_id = fields.Char(string='Id', readonly=True)
    shopify_order_id = fields.Char(string='Order Id', readonly=True)
    shopify_note = fields.Char(string='Note', readonly=True)
    shopify_user_id = fields.Char(string='User Id', readonly=True)
    shopify_processed_at = fields.Char(string='Processed At', readonly=True)
    shopify_restock = fields.Boolean(
        string='Shopify Restock',
    )
    shopify_admin_graphql_api_id = fields.Char(string='Admin Graphql Api Id', readonly=True)
    shopify_transaction_id = fields.Many2one(
        string='Transaction ID',
        comodel_name='shopify.transactions',
        ondelete='restrict',
    )
    #####################################################################
    ################Not RFequired########################################
    #####################################################################
    shopify_kind = fields.Char(string='Kind', readonly=True)
    shopify_gateway = fields.Char(string='Gateway', readonly=True)
    shopify_status = fields.Char(string='Status', readonly=True)
    shopify_message = fields.Char(string='Message', readonly=True)
    shopify_created_at = fields.Char(string='Created At', readonly=True)
    shopify_test = fields.Char(string='Test', readonly=True)
    shopify_authorization = fields.Char(string='Authorization', readonly=True)
    shopify_location_id = fields.Char(string='Location Id', readonly=True)
    shopify_parent_id = fields.Char(string='Parent Id', readonly=True)
    shopify_device_id = fields.Char(string='Device Id', readonly=True)
    shopify_error_code = fields.Char(string='Error Code', readonly=True)
    shopify_source_name = fields.Char(string='Source Name', readonly=True)
    shopify_receipt = fields.Char(string='Receipt', readonly=True)
    shopify_currency_exchange_adjustment = fields.Char(string='Currency Exchange Adjustment', readonly=True)
    shopify_amount = fields.Char(string='Amount', readonly=True)
    shopify_currency = fields.Char(string='Currency', readonly=True)
    refund_json = fields.Char(string='Refund JSON')


class ShopifyRefundsTransaction(models.Model):
    _name = 'shopify.refunds.transaction'
    _description = 'Shopify Refunds Transaction'
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
    shopify_refund_id = fields.Char(string='Shopify Id', readonly=True)
    shopify_refund_order_id = fields.Char(string='Order Id', readonly=True)
    shopify_refund_kind = fields.Char(string='Kind', readonly=True)
    shopify_refund_gateway = fields.Char(string='Gateway', readonly=True)
    shopify_refund_status = fields.Char(string='Status', readonly=True)
    shopify_refund_message = fields.Char(string='Message', readonly=True)
    shopify_refund_created_at = fields.Char(string='Created At', readonly=True)
    shopify_refund_test = fields.Char(string='Test', readonly=True)
    shopify_refund_authorization = fields.Char(string='Authorization', readonly=True)
    shopify_refund_location_id = fields.Char(string='Location Id', readonly=True)
    shopify_refund_user_id = fields.Char(string='User Id', readonly=True)
    shopify_refund_parent_id = fields.Char(string='Parent Id', readonly=True)
    shopify_refund_processed_at = fields.Char(string='Processed At', readonly=True)
    shopify_refund_device_id = fields.Char(string='Device Id', readonly=True)
    shopify_refund_error_code = fields.Char(string='Error Code', readonly=True)
    shopify_refund_source_name = fields.Char(string='Source Name', readonly=True)
    shopify_refund_receipt = fields.Char(string='Receipt', readonly=True)
    shopify_refund_currency_exchange_adjustment = fields.Char(string='Currency Exchange Adjustment', readonly=True)
    shopify_refund_amount = fields.Char(string='Amount', readonly=True)
    shopify_refund_currency = fields.Char(string='Currency', readonly=True)
    shopify_refund_admin_graphql_api_id = fields.Char(string='Admin Graphql Api Id', readonly=True)
    shopify_refund_payment_details = fields.Char(string='Payment Details', readonly=True)
    shopify_refund_payment_details_id = fields.Many2one(
        string='Payment Details IDs',
        comodel_name='shopify.payment.details',
        ondelete='restrict',
    )
    shopify_refund_payment_receipt_id = fields.Many2one(
        string='Receipt IDs',
        comodel_name='shopify.payment.receipt',
        ondelete='restrict',
    )
    shopify_refund_is_process = fields.Boolean(string="Is processed", default=False)
    shopify_refund_exchange_rate = fields.Char(string='Exchange Rate', readonly=True)
    shopify_refund_currency = fields.Char(string='Currency', readonly=True)
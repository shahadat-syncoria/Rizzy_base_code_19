# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
from dataclasses import field

from odoo import models, fields, exceptions, api, _
import logging

_logger = logging.getLogger(__name__)


class ShopifyFulfilment(models.Model):
    _name = "shopify.fulfilment"
    _description = "Shopify Fulfillment"
    _rec_name = "name"

    shopify_created_at = fields.Char(string='Created At')
    shopify_fulfilment_id = fields.Char(string='Shopify Fulfilment Id', readonly=True)

    name = fields.Char(string="Fulfilment")

    sale_order_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='restrict',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_order_id = fields.Char(string='Shopify Order ID', readonly=True)
    shopify_fulfilment_tracking_number = fields.Char(string='Tracking Number', readonly=True)
    shopify_tracking_company = fields.Char(string='Tracking Company', readonly=True)
    shopify_tracking_urls = fields.Char(string='Tracking URLS', readonly=True)

    shopify_fulfilment_service = fields.Char(string='Service', readonly=True)
    shopify_fulfilment_line = fields.One2many(
        comodel_name='shopify.fulfilment.line',
        inverse_name='shopify_fulfilment_id',
        string='Shopify Fulfilment Line',
        required=False)
    shopify_status = fields.Char(
        string='Status',
        required=False)
    shopify_shipment_status = fields.Char(
        string='Shipment Status',
        required=False)
    shopify_fulfilment_status = fields.Char(
        string='Fulfilment Status',
        required=False)
    shopify_location_id = fields.Char(string='Location Id')

class ShopifyFulfilmentLine(models.Model):
    _name = "shopify.fulfilment.line"
    _description = "Shopify Fulfillment Line"


    shopify_fulfilment_id = fields.Many2one(
        comodel_name='shopify.fulfilment',
        string='Shopify Fulfilment',
        required=False,invisible=1,ondelete='cascade')

    sale_order_id = fields.Many2one(
        string='Order',
        comodel_name='sale.order',
        ondelete='restrict',
    )
    shopify_instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
    )
    shopify_created_at = fields.Char(string='Created At')

    name = fields.Char(string="Fulfilment")

    shopify_fulfilment_line_id = fields.Char(string='Line Id', readonly=True)
    shopify_fulfilment_product_id = fields.Char(string=' Product Id', readonly=True)
    shopify_fulfilment_product_variant_id = fields.Char(string='Variant Id', readonly=True)
    shopify_fulfilment_product_title = fields.Char(string='Product Title Name', readonly=True)
    shopify_fulfilment_product_name = fields.Char(string='Product Name', readonly=True)
    shopify_fulfilment_product_sku = fields.Char(string='Product Sku', readonly=True)
    shopify_fulfilment_service = fields.Char(string='Fulfillment Service', readonly=True)
    shopify_fulfilment_qty = fields.Integer(string='Fulfilled Qty', readonly=True)
    shopify_fulfilment_grams = fields.Integer(string='Weight(grams) ', readonly=True)
    shopify_fulfilment_price = fields.Float(string='Price', readonly=True)
    shopify_fulfilment_total_discount = fields.Float(string='Discount', readonly=True)
    shopify_fulfilment_status = fields.Char(string='Status', readonly=True)





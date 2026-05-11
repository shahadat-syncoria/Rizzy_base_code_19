# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

# from odoo import models, fields, api, _
# import logging
# _logger = logging.getLogger(__name__)


# class MarketplaceSyncHistory(models.Model):
#     """Synchronisation History for Shopify and Odoo"""
#     _name = 'marketplace.sync.history'
#     _description = 'Synchronisation History for Quickbase and Odoo'


#     marketplace_type = fields.Selection([], string="Marketplace Type")
#     shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID")

#     name = fields.Char(
#         string='Name',
#         default="Sync History",
#         required=True,
#     )

#     last_product_sync = fields.Datetime(
#         string='Last Products Synced At',
#         default=fields.Datetime.now,
#     )
#     last_product_sync_id = fields.Integer(
#         string='Last Product Sync Id',
#     )
#     product_sync_no = fields.Integer(
#         string='No of Products Synced',
#     )

#     last_customer_sync = fields.Datetime(
#         string='Last Customer Sync at',
#         default=fields.Datetime.now,
#     )
#     last_customer_sync_id = fields.Integer(
#         string='Last Customer Sync Id',
#     )
#     customer_sync_no = fields.Integer(
#         string='No of Contact Synced',
#     )

#     last_order_sync = fields.Datetime(
#         string='Last Order Sync at',
#         default=fields.Datetime.now,
#     )
#     last_order_sync_id = fields.Integer(
#         string='Last Order Sync Id',
#     )
#     order_sync_no = fields.Integer(
#         string='No of Orders Synced',
#     )


#     def set_sync_history(self):
#         self.env['marketplace.sync.history']
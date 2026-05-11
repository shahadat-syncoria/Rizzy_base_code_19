# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from odoo import models, fields, exceptions, _, api
import logging
import re

_logger = logging.getLogger(__name__)


class UpdateStockWizard(models.TransientModel):
    _name = 'update.stock.wizard'
    _description = 'Stock Update Wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Import stock status'),
        ('from_odoo', 'Export stock status'),
        ('update_price', 'Update Price from Odoo To Marketplace')
    ], string="Operation Type")
    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
        required=True,
        domain="[('marketplace_state', '=', 'confirm')]"
    )
    # source_location_ids = fields.Many2many('stock.location', string="Source Location")
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")

    def update_stock_item(self):
        if self.instance_id:
            kwargs = {'marketplace_instance_id': self.instance_id}
            if hasattr(self, '%s_update_stock_item' % self.instance_id.marketplace_instance_type):
                return getattr(self, '%s_update_stock_item' % self.instance_id.marketplace_instance_type)(kwargs)


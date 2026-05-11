# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo.exceptions import UserError
from odoo import models, fields, api, _


class IrCron(models.Model):
    _inherit = 'ir.cron'

    shopify_stock_limit = fields.Integer(default=10)
    shopify_time_limit = fields.Integer(default=4)

    
    @api.onchange('shopify_time_limit')
    def _onchange_shopify_time_limit(self):
        for rec in self:
            if rec.shopify_time_limit and rec.shopify_time_limit > 4:
                raise UserError(_("Cron Time Cannot be greater than 4 minutes"))
    
    

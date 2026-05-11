# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class PosConfig(models.Model):
    _inherit = 'pos.config'
    
    @api.onchange('payment_method_ids')
    def _onchange_payment_method_ids(self):
        if len(self.payment_method_ids) > 0:
            method_ids = self.payment_method_ids.filtered(lambda payment_method: payment_method.use_payment_terminal == 'clover_cloud')
            for method in method_ids:
                if not method.clover_device_id:
                    # var = method._fields['use_payment_terminal'].selection
                    # method_name = dict(method._fields['use_payment_terminal'].selection).get(method.use_payment_terminal)
                    raise UserError(_("Your Payment Method %s has no devices allocated!" %(method.use_payment_terminal) ))

    
    # def _force_http(self):
    #     enforce_https = self.env['ir.config_parameter'].sudo().get_param('point_of_sale.enforce_https')
    #     if not enforce_https and self.payment_method_ids.filtered(lambda pm: pm.use_payment_terminal == 'clover_cloud'):
    #         return True
    #     return super(PosConfig, self)._force_http()


    



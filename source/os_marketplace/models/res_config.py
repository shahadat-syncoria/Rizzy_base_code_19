# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
from odoo import models, fields, api, exceptions, _

logger = logging.getLogger(__name__)


# class ResConfigSettings(models.TransientModel):
#     _inherit = 'res.config.settings'

#     marketplace_instance_id = fields.Many2one(
#         string='Select Instance',
#         comodel_name='marketplace.instance',
#         ondelete='restrict',
#     )

    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     marketplace_instance_id = ICPSudo.get_param(
    #         'syncoria_base_marketplace.marketplace_instance_id')
    #     marketplace_instance_id = self.env['marketplace.instance'].sudo().search(
    #         [('id', '=', marketplace_instance_id)])
    #     if marketplace_instance_id:
    #         res.update(
    #             marketplace_instance_id=marketplace_instance_id.id,
    #         )
    #     return res

    # def set_values(self):
    #     rec = super(ResConfigSettings, self).set_values()
    #     ICPSudo = self.env['ir.config_parameter'].sudo()
    #     # if self.marketplace_instance_id:
    #     ICPSudo.set_param("syncoria_base_marketplace.marketplace_instance_id", self.marketplace_instance_id.id)
    #     return rec



# class IrLogging(models.Model):
#     _inherit = 'ir.logging'

#     marketplace_type = fields.Selection([], string="Marketplace Type")
#     model_name = fields.Char(string='Model Name')
    



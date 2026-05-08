# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.addons.odoosync_base.utils.helper import is_module_installed
from odoo.exceptions import UserError

class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    
    account_id = fields.Many2one(
        string='account',
        comodel_name='omni.account',
        ondelete='restrict',
    )
    token = fields.Char(copy=False)
    omnisync_active = fields.Boolean(
        string='Connector Active',
        compute='_compute_omnisync_active' )

    def _compute_omnisync_active(self):
        for record in self:
            record.omnisync_active = False

    # def website_publish_button(self):
    #     res = super().website_publish_button()
    #     if self.is_published == True and self.delivery_type in ['canadapost', 'purolator']:
    #         is_os_delivery_website = is_module_installed('os_delivery_website')
    #         if not is_os_delivery_website:
    #             self.is_published = False
    #             raise UserError(_("Need to install Odoosync delivery website feature !!"))
    #     return res

    

    


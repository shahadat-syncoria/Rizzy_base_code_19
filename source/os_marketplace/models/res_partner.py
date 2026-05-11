# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")

        


    




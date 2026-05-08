# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models

class ResConfigSettingsForPurolator(models.TransientModel):
    _inherit = 'res.config.settings'

    module_delivery_purolator = fields.Boolean("Purolator")
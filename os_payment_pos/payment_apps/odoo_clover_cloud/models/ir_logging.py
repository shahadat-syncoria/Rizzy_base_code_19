# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields

class IrLogging(models.Model):
    _inherit = 'ir.logging'
    
    payment_method_id = fields.Many2one(
        string='Payment Method Id',
        comodel_name='pos.payment.method',
        ondelete='restrict',
    )
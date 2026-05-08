# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _

class Paymentprovider(models.Model):
    _inherit = 'payment.provider'

    
    account_id = fields.Many2one(
        string='account',
        comodel_name='omni.account',
        ondelete='restrict',
    )
    token = fields.Char(copy=False)
    omnisync_active = fields.Boolean(
        string='Active',
        compute='_compute_omnisync_active')

    def _compute_omnisync_active(self):
        for record in self:
            record.omnisync_active = False

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    ref = fields.Char(related='memo', string="Ref")


# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import base64
import json

import logging
from odoo import models, fields, api, _,SUPERUSER_ID
_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('resolve', 'Resolve Pay')], ondelete={'resolve': 'set default'})

    @api.model
    def toggle_resolvepay_menu_access(self,type):
        """Add or remove ResolvePay menu visibility based on provider existence"""
        group = self.env.ref('os_payment.group_resolvepay_active', raise_if_not_found=False)
        if not group:
            return

        admin_group = self.env.ref('base.group_user', raise_if_not_found=False)

        if not admin_group:
            return

        admin_users = admin_group.all_user_ids

        if type=='add':
            admin_users.write({'group_ids': [(4, group.id)]})  # Add group
        else:
            admin_users.write({'group_ids': [(3, group.id)]})  # Remove group

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.toggle_resolvepay_menu_access('add')
        return records

    def unlink(self):
        res = super().unlink()
        self.toggle_resolvepay_menu_access('pop')
        return res


class AccountPayment(models.Model):
    _inherit = "account.payment"

    resolvepay_payment_date = fields.Char("Resolve Pay payment datetime")
    rp_payout_transaction_id = fields.Char("Resolve Pay Payout Transaction Id")
    rp_payout_id = fields.Char("Resolve Pay Payout Id")
    rp_payout_transaction_type = fields.Selection(selection=[('advance', 'advance'),
                                                             ('payment', 'payment'),
                                                             ('refund', 'refund'),
                                                             ('monthly_fee', 'monthly_fee'), ('annual_fee', 'annual_fee'),
                                                             ('non_advanced_invoice_fee', 'non_advanced_invoice_fee'),
                                                             ('merchant_payment', 'merchant_payment'),
                                                             ('mdr_extension', 'mdr_extension'),
                                                             ('credit_note', 'credit_note')], string='Resolve Pay Transaction Type')
    rp_payout_transaction_amount_gross = fields.Float('amount_gross')
    rp_payout_transaction_amount_fee = fields.Float('amount_fee')
    rp_payout_transaction_amount_net = fields.Float('amount_net')
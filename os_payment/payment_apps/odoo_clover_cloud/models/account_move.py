# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging


class AccountMove(models.Model):
    _inherit = 'account.move'

    has_payments = fields.Boolean(
        compute="_compute_os_clover_reconciled_payment_ids",
        help="Technical field used for usability purposes")
    reconciled_payments_count = fields.Integer(
        compute="_compute_os_clover_reconciled_payment_ids")
    clover_last_action = fields.Char()

    clover_last_response = fields.Text()
    


    @api.depends('state')
    def _compute_os_clover_reconciled_payment_ids(self):
        for record in self:
            record.reconciled_payments_count = 0
            if record.move_type == 'out_invoice' and record.name != '/' and record.state != 'draft':
                domain = [('ref', 'like', record.name),
                            ('payment_method_line_id.code', '=', 'electronic'),
                            ('payment_type', '=', 'outbound') ]


                AccPayment = self.env['account.payment']
                payments = AccPayment.search(domain)
                record.has_payments = bool(payments.ids)
                record.reconciled_payments_count = len(payments)

    def button_open_payments(self):
        ''' Redirect the user to the payments for this invoice.
        :return:    An action on account.payment.
        '''
        self.ensure_one()

        domain = [('ref', 'like', self.name),
                    ('payment_method_line_id.code', '=', 'electronic'),
                    ('payment_type', '=', 'outbound') ]

        AccPayment = self.env['account.payment']
        if self.move_type == 'out_refund':
            print("ref", self.ref)
            domain = ['|',
                        ('ref', 'like', self.ref),
                        ('payment_method_line_id.code', '=', 'electronic'), 
                        ('payment_type', '=', 'outbound'),
                        ]
        payments = AccPayment.search(domain)

        tree_view = self.env.ref('odoo_clover_cloud.account_payment_view_clover')
        fomr_view = self.env.ref('account.view_account_payment_form')
        
        action = {
            'name': _("Invoice Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': True},
            'view_type': 'list',
            'view_mode': 'list,form',
            'domain': [('id', 'in', payments.ids)],
            'views': [(tree_view.id, 'list'), (fomr_view.id, 'form')],
            'view_id': tree_view.id,
            }
        return action

    def write_vals(self, vals):
        if type(self.id) == list:
            self = self.browse(self.id)
        for rec in self:
            rec.write(vals)
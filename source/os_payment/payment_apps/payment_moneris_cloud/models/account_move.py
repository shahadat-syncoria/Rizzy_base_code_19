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

    moneris_request_id = fields.Char()
    moneris_last_action = fields.Char()
    moneris_transaction_id = fields.Char()
    moneris_idempotency_key = fields.Char()
    has_payments = fields.Boolean(
        compute="_compute_os_moneris_cloud_reconciled_payment_ids", help="Technical field used for usability purposes")
    reconciled_payments_count = fields.Integer(
        compute="_compute_os_moneris_cloud_reconciled_payment_ids")


    @api.depends('state')
    def _compute_os_moneris_cloud_reconciled_payment_ids(self):
        for record in self:
            record.reconciled_payments_count = 0
            if record.move_type == 'out_invoice' and record.name != '/' and record.state != 'draft':
                domain = [('ref', 'like', record.name),
                            ('payment_method_id.code', '=', 'electronic'),
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
                    ('payment_method_id.code', '=', 'electronic'),
                    ('payment_type', '=', 'outbound') ]

        AccPayment = self.env['account.payment']
        if self.move_type == 'out_refund':
            print("ref", self.ref)
            # TO DO: CONFUSION HERE
            domain = ['|',
                        ('moneris_transaction_id', 'like', self.name),
                        ('ref', 'like', self.ref),
                        ('payment_method_id.code', '=', 'electronic'), 
                        ('payment_type', '=', 'outbound'),
                        ]
        payments = AccPayment.search(domain)

        tree_view = self.env.ref('payment_moneris_cloud.account_payment_view_moneris')
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


    # def action_post(self):
    #     if self.move_type == 'out_refund':
    #         split_name = "Reversal of: "
    #         if self.env.user.lang in ['fr_FR', 'fr_BE' , 'fr_CA', 'fr_CH']:
    #             split_name = 'Extourne de : '
    #         print(self.display_name)
    #         inv_name = self.display_name
    #         inv_name = inv_name.split(split_name)[1].split(",")[0]
    #         invoice = self.env['account.move'].sudo().search([('name','=',inv_name)])
    #         inv_amt = invoice.amount_residual
    #         domain = [('ref', 'like', inv_name),
    #                     ('payment_method_id.code', '=', 'electronic'),
    #                     ('payment_type', '=', 'outbound') ,
    #                     ('state','=','posted')]
    #         AccPayment = self.env['account.payment']
    #         refunds = AccPayment.search(domain)
    #
    #         if len(refunds) > 0 :
    #             refunds_sum = sum(refunds.mapped('amount'))
    #             print("\n self.amount-->", self.amount_residual,
    #                 "\n invoice.amount-->",  invoice.amount_total,
    #                 "\n refunds_sum-->", refunds_sum)
    #             if self.amount_residual >  invoice.amount_total - refunds_sum:
    #                 raise UserError(_('You can not refund with this amount'))
    #
    #     super(AccountMove, self).action_post()
        
        
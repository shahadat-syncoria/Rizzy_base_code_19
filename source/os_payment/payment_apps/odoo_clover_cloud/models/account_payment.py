# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.tools import float_is_zero
import logging

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    clover_success = fields.Char(string='Success', )
    clover_result = fields.Char(string='Result', )
    clover_payment_id = fields.Char(string='Payment Id', )
    clover_order_id = fields.Char(string='Order Id', )
    clover_tender_id = fields.Char(string='Tender Id', )
    clover_amount = fields.Char(string='Clover Amt.', )
    clover_ext_id = fields.Char(string='External Payment Id', )
    clover_emp_id = fields.Char(string='Employee Id', )
    clover_created_time = fields.Char(string='Created Time', )
    clover_payment_result = fields.Char(string='Payment Result', )

    clover_card_type = fields.Char(string='Card Type', )
    clover_entry_type = fields.Char(string='Entry Type', )
    clover_type = fields.Char(string='Clover Type', )
    clover_auth_code = fields.Char(string='Auth Code', )
    clover_reference_id = fields.Char(string='Reference Id', )
    clover_transaction_no = fields.Char(string='Transaction No', )
    clover_state = fields.Char(string='State', )
    clover_last_digits = fields.Char(string='Last 4 digits', )
    clover_cardholder_name = fields.Char(string='Cardholder Name', )
    clover_expiry_date = fields.Char(string='Expiry Date', )
    clover_token = fields.Char(string='Token', )
    clover_response = fields.Char(string='Clover Response', )
    # Refund Parts
    clover_device_id = fields.Char(string='Device Id', )
    clover_refund_reason = fields.Char(string='Reason', )
    clover_message = fields.Char(string='Message', )
    clover_refund_id = fields.Char(string='Refund Id', )
    clover_tax_amount = fields.Char(string='Tax Amt.', )
    clover_client_created_time = fields.Char(string='Client Created Time', )
    clover_voided = fields.Char(string='Voided', )
    clover_transaction_info = fields.Char(string='Transaction Info', )
    clover_refund_source_payment_id = fields.Many2one(
        'account.payment',
        string='Clover Refund Source Payment',
        copy=False,
        readonly=True,
    )
    clover_refunded_amount = fields.Monetary(
        string='Clover Refunded Amount',
        currency_field='currency_id',
        compute='_compute_clover_refund_balances',
    )
    clover_refundable_amount = fields.Monetary(
        string='Clover Refundable Amount',
        currency_field='currency_id',
        compute='_compute_clover_refund_balances',
    )

    has_payments = fields.Boolean(
        compute="_compute_clover_reconciled_payment_ids", default=False)
    reconciled_payments_count = fields.Integer(
        compute="_compute_clover_reconciled_payment_ids")
    clover_is_samecard = fields.Boolean(string="Is Same Card?",
                                        compute="_compute_clover_is_samecard", )

    is_clover_refunded = fields.Boolean(string="Is Clover Refunded?", default=False)

    @api.depends('amount', 'payment_type', 'clover_payment_id', 'state', 'clover_refund_source_payment_id')
    def _compute_clover_refund_balances(self):
        for record in self:
            record.clover_refunded_amount = 0.0
            record.clover_refundable_amount = 0.0

            if record.payment_type != 'inbound' or not record.clover_payment_id:
                continue

            refunds = self.search([
                ('id', '!=', record.id),
                ('payment_type', '=', 'outbound'),
                ('state', '!=', 'cancel'),
                '|',
                ('clover_refund_source_payment_id', '=', record.id),
                '&',
                ('clover_refund_source_payment_id', '=', False),
                ('clover_payment_id', '=', record.clover_payment_id),
            ])

            record.clover_refunded_amount = sum(refunds.mapped('amount'))
            record.clover_refundable_amount = max(record.amount - record.clover_refunded_amount, 0.0)

    def _sync_clover_refund_state(self):
        for record in self.filtered(lambda payment: payment.payment_type == 'inbound' and payment.clover_payment_id):
            rounding = record.currency_id.rounding or 0.01
            record.is_clover_refunded = float_is_zero(
                record.clover_refundable_amount,
                precision_rounding=rounding,
            )

    @api.depends('payment_type')
    def _compute_clover_is_samecard(self):
        for record in self:
            record.clover_is_samecard = False
            if record.payment_type == 'outbound' and record.payment_method_line_id.code == 'electronic' and \
                    record.move_id.journal_id.use_clover_terminal == True:
                inv_name = False
                if len(record.reconciled_invoice_ids) == 1:
                    inv_name = record.move_id.display_name.split("Reversal of: ")[1].split(",")[0].replace(")", "")
                if len(record.reconciled_invoice_ids) > 1:
                    inv_name = record.move_id.display_name.split("(")[1].replace(")", "")
                _logger.info("\ninv_name-->" + str(inv_name))
                domain = [('ref', 'like', inv_name),
                          ('payment_type', '=', 'inbound'),
                          ('clover_last_digits', '=', record.clover_last_digits)]
                payments = record.search(domain)
                _logger.info("\npayments, " + str(payments))
                if len(payments) > 0:
                    record.clover_is_samecard = True

    @api.depends('clover_last_digits')
    def _compute_clover_reconciled_payment_ids(self):
        for record in self:
            record.has_payments = False
            record.reconciled_payments_count = 0
            if record.payment_type == 'inbound':
                domain = [('ref', 'like', record.ref),
                          # ('move_id.id','=',self.move_id.id),
                          ('payment_type', '=', 'outbound'),
                          ('clover_last_digits', '=', record.clover_last_digits)]
                payments = self.search(domain)
                _logger.info("\npayments, " + str(payments))
                record.has_payments = bool(payments.ids)
                record.reconciled_payments_count = len(payments)

    def button_open_payments(self):
        ''' Redirect the user to the invoice(s) paid by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Invoice Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        domain = [('ref', 'like', self.ref),
                  ('payment_type', '=', 'outbound'),
                  ('clover_last_digits', '=', self.clover_last_digits)]
        payments = self.search(domain)

        tree_view = self.env.ref('payment_clover_clover_invoice.account_payment_view_clover')
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

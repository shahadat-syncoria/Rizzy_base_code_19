from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class Payout(models.Model):
    _name = 'resolvepay.payout'

    payout_id = fields.Char('ID')
    payout_amount_gross = fields.Float('Amount Gross')
    payout_amount_fee = fields.Float('Amount Fee')
    payout_amount_net = fields.Float('Amount Net')
    payout_status = fields.Char('Status')
    payout_retry_payout_id = fields.Char('Payout id being retried.')
    payout_failed_at = fields.Char('Failed At')
    payout_expected_by = fields.Char('Expected By')
    payout_transactions_starting_at = fields.Char('Transaction Starting At')
    payout_transactions_ending_at = fields.Char('Transaction Ending At')
    payout_canceled_at = fields.Char('Canceled At')
    payout_created_at = fields.Char('Created At')
    payout_updated_at = fields.Char('Updated At')


class PayoutTransaction(models.Model):
    _name = 'resolvepay.payout.transaction'

    transaction_id = fields.Char('ID')
    transaction_payout_id = fields.Char('Payout ID')
    transaction_type = fields.Selection(selection=[('advance', 'advance'),
                                       ('payment', 'payment'),
                                       ('refund', 'refund'),
                                       ('monthly_fee', 'monthly_fee'), ('annual_fee', 'annual_fee'),
                                       ('non_advanced_invoice_fee', 'non_advanced_invoice_fee'),
                                       ('merchant_payment', 'merchant_payment'),
                                       ('mdr_extension', 'mdr_extension'),
                                       ('credit_note', 'credit_note')], string='Resolve Pay Transaction Type')
    transaction_customer_id = fields.Char('Customer ID')
    transaction_customer_name = fields.Char('Customer Name')
    transaction_invoice_id = fields.Char('Invoice ID')
    transaction_invoice_number = fields.Char('Invoice Number')
    transaction_order_id = fields.Char('Order Id')
    transaction_po_number = fields.Char('PO Number')
    transaction_amount_gross = fields.Float('Amount Gross')
    transaction_amount_fee = fields.Float('Amount Fee')
    transaction_amount_net = fields.Float('Amount Net')
    transaction_created_at = fields.Char('Created At')
    transaction_updated_at = fields.Char('Updated At')

    move_id = fields.Many2one(comodel_name='account.move')

import base64

from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json, time
from datetime import date
import logging
_logger = logging.getLogger(__name__)


class Invoice(models.Model):
    _inherit = 'account.move'

    resolvepay_id = fields.Char(string='ResolvePay Invoice ID', tracking=True, copy=False)
    resolvepay_source = fields.Char(string='ResolvePay Source')
    resolvepay_customer_id = fields.Char(string='ResolvePay Customer ID', help='ID of the customer being charged.')
    resolvepay_order_number = fields.Char(string='Order Number', help='Order number identifier.')
    resolvepay_number = fields.Char(string='Invoice Number', help='Invoice number identifier.')
    resolvepay_po_number = fields.Char(string='PO Number', help='PO number identifier.')
    resolvepay_notes = fields.Char(string='Notes', help='Additional notes for the Customer')
    resolvepay_line_items = fields.Char(string='Line items', help='Line item data')
    resolvepay_merchant_invoice_url = fields.Char(string='Merchant invoice URL', help='The invoice PDF that you have uploaded to Resolve.')
    resolvepay_resolve_invoice_url = fields.Char(string='Resolve invoice URL', help='Resolve-issued invoice PDF with your invoice attached.')
    resolvepay_resolve_invoice_status = fields.Char(string='Invoice status', help='Shows current status of the Resolve-issued invoice PDF.')
    resolvepay_fully_paid_at = fields.Char(string='Fully paid at', help='The date the invoice has been fully paid.')
    resolvepay_advanced = fields.Boolean(string='Advanced', help='Indicates whether the invoice has been advanced.')
    resolvepay_due_at = fields.Char(string='Due at', help='The current due date for this invoice payment.')
    resolvepay_original_due_at = fields.Char(string='Original due at', help='The due date for this invoice at the time an advance was issued.')
    resolvepay_invoiced_at = fields.Char(string='Invoiced at', help='The date this invoice was created in your system of record (Resolve or Quickbooks).')
    resolvepay_advance_requested = fields.Boolean(string='Advance requested', help='Indicated if advance was requested.')
    resolvepay_terms = fields.Char(string='Terms', help='The terms selected for this invoice.')
    resolvepay_amount_payout_due = fields.Float(string='Amount payout due', help='The original amount that Resolve owed on this invoice on the advance date.')
    resolvepay_amount_payout_paid = fields.Float(string='Amount payout paid', help='The amount that Resolve has paid out.')
    resolvepay_amount_payout_pending = fields.Float(string='Amount payout pending', help='The amount that Resolve has currently pending to be paid out.')
    resolvepay_amount_payout_refunded = fields.Float(string='Amount payout refunded', help='The amount that Resolve has debited from due to refunds.')
    resolvepay_amount_payout_balance = fields.Float(string='Amount payout balance', help='The amount remaining to be paid out.')
    resolvepay_payout_fully_paid = fields.Float(string='Payout fully paid', help='The status of whether or not this invoice has been fully paid out.')
    resolvepay_payout_fully_paid_at = fields.Char(string='Payout fully paid at', help='The date of when this invoice has been fully paid out.')
    resolvepay_amount_balance = fields.Float(string='Amount balance', help='Current balance due.')
    resolvepay_amount_due = fields.Float(string='Amount due', help='Original amount due')
    resolvepay_amount_refunded = fields.Float(string='Amount refunded', help='Amount that has been refunded.')
    resolvepay_amount_pending = fields.Float(string='Amount pending', help='Amount of total payments pending.')
    resolvepay_amount_paid = fields.Float(string='Amount paid', help='Amount of total payments applied to this invoice.')
    resolvepay_amount_advance = fields.Float(string='Amount advance', help='Amount of advance received.')
    resolvepay_amount_advance_fee = fields.Float(string='Amount advance fee', help='Fee for the amount of advance.')
    resolvepay_amount_advance_fee_refund = fields.Float(string='Amount advance fee refund', help='Refunded fees for the amount of advance.')
    resolvepay_advance_rate = fields.Float(string='Advance rate', help='The advance rate that was used to determine amount of advance')
    resolvepay_advanced_at = fields.Char(string='Advanced at', help='The date this invoice was advanced.')
    resolvepay_amount_customer_fee_total = fields.Float(string='Amount customer fee total', help='The total amount of customer fees accrued.')
    resolvepay_amount_customer_fee_waived = fields.Float(string='Amount customer fee waived', help='The total amount of customer fees waived.')
    resolvepay_amount_customer_fee_paid = fields.Float(string='Amount customer fee paid', help='The total amount of customer fees paid.')
    resolvepay_amount_customer_fee_balance = fields.Float(string='Amount customer fee balance', help='The current amount of customer fees owed.')
    resolvepay_created_at = fields.Char(string='Created at', help='Date the customer was created.')
    resolvepay_updated_at = fields.Char(string='Updated at', help='Date the customer was last updated.')
    resolvepay_archived = fields.Char(string='Archived', help='Boolean indicating if invoice is archived.')

    resolvepay_charge_id = fields.Char(string='ResolvePay Charge Id')
    resolvepay_amount_available = fields.Float(string='Available Credit', related='partner_id.resolvepay_amount_available')

    payout_transaction_ids = fields.One2many(comodel_name='resolvepay.payout.transaction', inverse_name='move_id', string='Payout Transaction')

    def action_update_resolvepay_payments(self):
        date_params_end = fields.Datetime.now().strftime("%Y-%m-%dT23:59:59.000Z")
        resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
        payload = {
            'filter': '?sort=-created_at&status=paid&limit=100&filter[expected_by][lte]=' + date_params_end
        }
        res = resolvepay_instance._post_request(payload, service_type='get_payouts')
        payouts = res.get('results')
        for payout in payouts:
            _logger.info(payout)
            payout_res = self.env['resolvepay.payout'].search([('payout_id', '=', payout['id'])])
            if payout_res:
                continue
            if payout.get('status') != 'paid':
                continue
            payment_date = payout.get('expected_by')
            payout_id = payout.get('id')
            payload = {
                'filter': '?filter[payout_id]=' + payout_id
            }
            res = resolvepay_instance._post_request(payload, service_type='get_payout_transactions')
            if res.get('results'):
                payout_transactions = res.get('results')
                for payout_transaction in payout_transactions:
                    _logger.info(payout_transaction)
                    invoice_id = payout_transaction.get('invoice_id', False)
                    if not invoice_id:
                        continue
                    invoice = self.search([('resolvepay_id', '=', invoice_id)], limit=1)
                    if not invoice:
                        _logger.info('Cannot find RP invoice: ' + invoice_id)
                    if invoice.state == 'posted' and invoice.payment_state in ('partial', 'not_paid'):
                        self.register_resolvepay_payment(invoice, payout_transaction, payment_date)
                    self.create_payout_transaction(invoice, payout_transaction)
            self.create_payout(payout)

    def create_invoice_resolvepay(self):
        for record in self:
            if record.state != 'posted':
                raise UserError('This invoice is in draft mode')
            if record.resolvepay_id:
                raise UserError('This invoice is already exported. ResolvePay ID: ' + record.resolvepay_id)
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            if len(resolvepay_instance):
                resolvepay_customer = False
                resolvepay_customer_id = False
                if record.partner_id.resolvepay_id:
                    resolvepay_customer = True
                    resolvepay_customer_id = record.partner_id.resolvepay_id
                elif record.partner_id.parent_id:
                    if record.partner_id.parent_id.resolvepay_id:
                        resolvepay_customer = True
                        resolvepay_customer_id = record.partner_id.parent_id.resolvepay_id
                if not resolvepay_customer:
                    raise ValidationError('This customer does not exist in ResolvePay')

                # pdf = self.env.ref('account.account_invoices_without_payment')._render_qweb_pdf(record.id)
                if resolvepay_instance.template_id:
                    pdf = self.env['ir.actions.report']._render_qweb_pdf(resolvepay_instance.template_id.id, res_ids=record.id)
                else:
                    pdf = self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices_without_payment', res_ids=record.id)
                filename = record.name.replace('/', '_') + '.pdf'
                invoice_pdf = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf[0]),
                    'res_model': 'account.move',
                    'res_id': record.id,
                    'mimetype': 'application/pdf',
                    'public': True
                })
                self._cr.commit()
                web_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                pdf_url = web_base_url + '/web/content/' + str(invoice_pdf.id)

                if record.invoice_origin:
                    invoice_data = dict(
                        amount=record.amount_residual,
                        customer_id=resolvepay_customer_id,
                        number=record.name,
                        order_number=record.invoice_origin,
                        merchant_invoice_url=pdf_url
                    )
                else:
                    invoice_data = dict(
                        amount=record.amount_residual,
                        customer_id=resolvepay_customer_id,
                        number=record.name,
                        merchant_invoice_url=pdf_url
                    )
                _logger.info('REQUEST DATA RESOLVE')
                _logger.info(invoice_data)
                res = resolvepay_instance._post_request(invoice_data, service_type='create_invoice')
                if res:
                    record.message_post(
                        body="Export to ResolvePay successfully. ResolvePay Invoice ID: {}".format(res.get('id')))
                    invoice_value = {}
                    for key, value in res.items():
                        if 'resolvepay_' + key in self._fields:
                            invoice_value['resolvepay_' + key] = value
                    record.write(invoice_value)
            else:
                raise UserError('There is no ResolvePay instance exists')

    def update_invoice_resolvepay(self):
        for record in self:
            if not record.resolvepay_id:
                continue
            if record.state != 'posted':
                raise UserError('This invoice is in draft mode')
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            if len(resolvepay_instance):
                resolvepay_customer = False
                resolvepay_customer_id = False
                if record.partner_id.resolvepay_id:
                    resolvepay_customer = True
                    resolvepay_customer_id = record.partner_id.resolvepay_id
                elif record.partner_id.parent_id:
                    if record.partner_id.parent_id.resolvepay_id:
                        resolvepay_customer = True
                        resolvepay_customer_id = record.partner_id.parent_id.resolvepay_id
                if not resolvepay_customer:
                    raise ValidationError('This customer does not exist in ResolvePay')

                # pdf = self.env.ref('account.account_invoices_without_payment')._render_qweb_pdf(record.id)
                if resolvepay_instance.template_id:
                    pdf = self.env['ir.actions.report']._render_qweb_pdf(resolvepay_instance.template_id.id, res_ids=record.id)
                else:
                    pdf = self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices_without_payment', res_ids=record.id)
                filename = record.name.replace('/', '_') + '.pdf'
                invoice_pdf = self.env['ir.attachment'].create({
                    'name': filename,
                    'type': 'binary',
                    'datas': base64.b64encode(pdf[0]),
                    'res_model': 'account.move',
                    'res_id': record.id,
                    'mimetype': 'application/pdf',
                    'public': True
                })
                self._cr.commit()
                web_base_url = self.env['ir.config_parameter'].get_param('web.base.url')
                pdf_url = web_base_url + '/web/content/' + str(invoice_pdf.id)

                if record.invoice_origin:
                    invoice_data = dict(
                        amount=record.amount_residual,
                        customer_id=resolvepay_customer_id,
                        number=record.name,
                        order_number=record.invoice_origin,
                        merchant_invoice_url=pdf_url,
                        invoice_id=record.resolvepay_id
                    )
                else:
                    invoice_data = dict(
                        amount=record.amount_residual,
                        customer_id=resolvepay_customer_id,
                        number=record.name,
                        merchant_invoice_url=pdf_url,
                        invoice_id=record.resolvepay_id
                    )
                _logger.info('REQUEST DATA TO UPDATE RESOLVE')
                _logger.info(invoice_data)
                res = resolvepay_instance._post_request(invoice_data, service_type='update_invoice')
                if res:
                    record.message_post(
                        body="Update to ResolvePay successfully. ResolvePay Invoice ID: {}".format(res.get('id')))
                    invoice_value = {}
                    for key, value in res.items():
                        if 'resolvepay_' + key in self._fields:
                            invoice_value['resolvepay_' + key] = value
                    record.write(invoice_value)
            else:
                raise UserError('There is no ResolvePay instance exists')

    def get_payout_info(self, payout_id):
        resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
        payload = {
            'payout_id': payout_id
        }
        res = resolvepay_instance._post_request(payload, service_type='get_payout')
        return res

    def register_resolvepay_payment(self, invoice, payout_transaction, arrive_date):
        payout_transaction_id = payout_transaction.get('id')
        payout_id = payout_transaction.get('payout_id')
        amount_gross = payout_transaction.get('amount_gross')
        amount_fee = payout_transaction.get('amount_fee')
        amount_net = payout_transaction.get('amount_net')
        payment_type = payout_transaction.get('type')
        invoice_id = payout_transaction.get('invoice_id', False)
        payment_id = self.env['account.payment'].search([('rp_payout_transaction_id', '=', payout_transaction_id)])
        if payment_id:
            return
        if payment_type not in ('advance', 'payment'):
            return
        if amount_gross > invoice.amount_residual:
            return
        if invoice_id == invoice.resolvepay_id and invoice.payment_state in ('not_paid', 'partial'):
            _logger.info('CREATE NEW PAYMENT')
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            journal = resolvepay_instance.journal_id
            if not journal:
                raise ValidationError('Can not find ResolvePay journal')
            payment_dict = {
                'journal_id': journal.id,
                'amount': amount_gross,
                'payment_date': arrive_date,
            }
            payment_method_line_id = journal.inbound_payment_method_line_ids
            if payment_method_line_id:
                payment_dict['payment_method_line_id'] = payment_method_line_id[0].id
                pmt_wizard = self.env['account.payment.register'].with_context(
                    active_model='account.move', active_ids=invoice.ids).create(payment_dict)
                new_payment_id = pmt_wizard._create_payments()
                new_payment_id.write({'rp_payout_transaction_id': payout_transaction_id,
                                      'rp_payout_id': payout_id,
                                      'rp_payout_transaction_type': payment_type,
                                      'rp_payout_transaction_amount_gross': amount_gross,
                                      'rp_payout_transaction_amount_fee': amount_fee,
                                      'rp_payout_transaction_amount_net': amount_net})
                invoice_id.partner_id.fetch_customer_resolvepay()

    def resolvepay_fetch_invoice_payments(self):
        for invoice in self:
            if invoice.state == 'cancel':
                continue
            if invoice.state == 'draft':
                raise UserError('This invoice is not confirmed '+invoice.name)
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            payload = {
                'filter': '?filter[invoice_id]=' + invoice.resolvepay_id
            }
            res = resolvepay_instance._post_request(payload, service_type='get_payout_transactions')
            if res.get('results'):
                data = res.get('results', [])
                _logger.info("Payout Transactions data =====> %s", data)
                try:
                    for payout_transaction in data:
                        _logger.info(payout_transaction)
                        payout_id = payout_transaction.get('payout_id')
                        payout_info = self.get_payout_info(payout_id)
                        if payout_info.get('status') != 'paid':
                            return
                        payout_arrive_date = payout_info.get('expected_by')
                        self.register_resolvepay_payment(invoice, payout_transaction, payout_arrive_date)
                        self.create_payout_transaction(self, payout_transaction)
                except Exception as e:
                    _logger.info("Exception-{}".format(e))
                    raise ValidationError(e)

    def create_payout_transaction(self, invoice, payout_transaction):
        val_dict = {}
        for key, value in payout_transaction.items():
            val_dict['transaction_'+key] = value
        val_dict['move_id'] = invoice.id
        _logger.info(val_dict)
        payout_transaction_id = self.env['resolvepay.payout.transaction'].search([('transaction_id', '=', val_dict['transaction_id'])])
        if not payout_transaction_id:
            self.env['resolvepay.payout.transaction'].create(val_dict)

    def create_payout(self, payout):
        val_dict = {}
        for key, value in payout.items():
            val_dict['payout_'+key] = value
        _logger.info(val_dict)
        payout_id = self.env['resolvepay.payout'].search([('payout_id', '=', val_dict['payout_id'])])
        if not payout_id:
            self.env['resolvepay.payout'].create(val_dict)

    def get_resolve_invoice_info(self):
        for invoice in self:
            if not invoice.resolvepay_id:
                raise ValidationError('Invoice does not have Resolve Pay ID. Cannot update invoice ' + invoice.name)
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            if resolvepay_instance:
                payload = {
                    'invoice_id': invoice.resolvepay_id
                }
                res = resolvepay_instance._post_request(payload, service_type='get_invoice')
                invoice_value = {}
                for key, value in res.items():
                    if 'resolvepay_' + key in self._fields:
                        invoice_value['resolvepay_' + key] = value
                invoice.write(invoice_value)
            else:
                raise UserError('There is no ResolvePay instance')

    def action_update_resolvepay_invoice_info(self):
        invoices = self.env['account.move'].search([])
        to_update = invoices.filtered(lambda i: i.resolvepay_id)
        if not to_update:
            return
        for rec in to_update:
            try:
                time.sleep(0.5)
                rec.get_resolve_invoice_info()
            except Exception as e:
                _logger.error(e)
                continue

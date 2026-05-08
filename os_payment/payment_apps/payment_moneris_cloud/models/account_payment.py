# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.tools import float_is_zero
import logging
from odoo.exceptions import UserError
import os
import datetime
import base64
from fpdf import FPDF
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    cloud_terminal_payment = fields.Boolean(
        string='Is Moneris Terminal Payment?')

    is_moneris_refunded = fields.Boolean(string="Is Refunded?",default=False)

    cloud_request_id = fields.Char("Cloud Request ID")
    purchase_cloud_ticket = fields.Char()
    payment_provider_name = fields.Char()
    purchase_receipt_id = fields.Char()
    # purchase_transaction_id = fields.Char()

    cloud_val_responsecode = fields.Char("Validation Response Code")
    cloud_val_message = fields.Char("Validation Message")
    cloud_val_completed = fields.Char("Validation Completed")
    cloud_val_error = fields.Char("Validation Error")
    cloud_val_timeout = fields.Char("Validation Timeout")
    cloud_val_postbackurl = fields.Char("Validation Postback Url")
    cloud_val_cloudticket = fields.Char("Validation Cloud Ticket")

    moneris_cloud_completed = fields.Boolean("Completed")
    moneris_cloud_transtype = fields.Char("Trans Type")
    moneris_cloud_error = fields.Boolean("Error")
    moneris_cloud_initrequired = fields.Boolean("Init Required")
    moneris_cloud_safindicator = fields.Char("Saf Indicator")
    moneris_cloud_responsecode = fields.Char("Response Code")
    moneris_cloud_iso = fields.Char("ISO")
    moneris_cloud_languagecode = fields.Char("Language Code")
    moneris_cloud_partailauthamount = fields.Char("Partial Auth Amount")
    moneris_cloud_availablebalance = fields.Char("Available Balance")
    moneris_cloud_tipamount = fields.Char("TipAmount")
    moneris_cloud_emvcashbackamount = fields.Char("EMV Cash Back Amount")
    moneris_cloud_surchargeamount = fields.Char("Surcharge Amount")
    moneris_cloud_foreigncurrencyamount = fields.Char(
        "Foreign Currency Amount")
    moneris_cloud_baserate = fields.Char("Base Rate")
    moneris_cloud_exchangerate = fields.Char("ExchangeRate")
    moneris_cloud_pan = fields.Char("Pan")
    moneris_cloud_cardtype = fields.Char("Card Type")
    moneris_cloud_cardname = fields.Char("Card Name")
    moneris_cloud_accounttype = fields.Char("Account Type")
    moneris_cloud_swipeindicator = fields.Char("Swipe Indicator")
    moneris_cloud_formfactor = fields.Char("FormF actor")


    moneris_cloud_cvmindicator = fields.Char("Cvm Indicator")
    moneris_cloud_reservedfield1 = fields.Char("Reserved Field1")
    moneris_cloud_reservedfield2 = fields.Char("Reserved Field2")
    moneris_cloud_authcode = fields.Char("Auth Code")
    moneris_cloud_invoicenumber = fields.Char("Invoice Number")
    moneris_cloud_emvechodata = fields.Char("EMV Echo Data")
    moneris_cloud_reservedfield3 = fields.Char("Reserved Field3")
    moneris_cloud_reservedfield4 = fields.Char("Reserved Field4")
    moneris_cloud_aid = fields.Char("AID")
    moneris_cloud_applabel = fields.Char("App Label")
    moneris_cloud_apppreferredname = fields.Char("App Preferred Name")
    moneris_cloud_arqc = fields.Char("Arqc")
    moneris_cloud_tvrarqc = fields.Char("TvrArqc")
    moneris_cloud_tcacc = fields.Char("Tcacc")
    moneris_cloud_tvrtcacc = fields.Char("TvrTcacc")
    moneris_cloud_tsi = fields.Char("Tsi")
    moneris_cloud_tokenresponsecode = fields.Char("Token Response Code")
    moneris_cloud_token = fields.Char("Token")
    moneris_cloud_logonrequired = fields.Char("Logon Required")
    moneris_cloud_cncryptedcardinfo = fields.Char("Encrypted Card Info")
    moneris_cloud_transdate = fields.Char("Trans Date")
    moneris_cloud_transtime = fields.Char("Trans Time")
    moneris_cloud_amount = fields.Char("Moneris Amount")
    moneris_cloud_referencenumber = fields.Char("Reference Number")
    moneris_cloud_receiptid = fields.Char("Receipt Id")
    moneris_cloud_transid = fields.Char("Trans Id")
    moneris_cloud_timeout = fields.Char("TimedOut")
    moneris_cloud_cloudticket = fields.Char("Cloud Ticket")
    moneris_cloud_txnname = fields.Char("TxnName")

    cloud_is_samecard = fields.Boolean(string="Is Same Card?",
        compute="_compute_cloud_is_samecard",)

    moneris_refund_source_payment_id = fields.Many2one(
        'account.payment',
        string='Moneris Refund Source Payment',
        copy=False,
        readonly=True,
    )
    moneris_refunded_amount = fields.Monetary(
        string='Moneris Refunded Amount',
        currency_field='currency_id',
        compute='_compute_moneris_refund_balances',
    )
    moneris_refundable_amount = fields.Monetary(
        string='Moneris Refundable Amount',
        currency_field='currency_id',
        compute='_compute_moneris_refund_balances',
    )

    attachment_id = fields.Many2one(
        string='Payment Attachment',
        comodel_name='ir.attachment',
        ondelete='restrict',
    )
    merchant_attachment_id = fields.Many2one(
        string='Payment Attachment ',
        comodel_name='ir.attachment',
        ondelete='restrict',
    )
    moneris_receipt = fields.Binary(string="Moneris Receipt", related="attachment_id.datas")
    moneris_receipt_name = fields.Char(string="Moneris Receipt Name", related="attachment_id.name")

    moneris_merchant_receipt = fields.Binary(string="Moneris Merchant Receipt", related="merchant_attachment_id.datas")
    moneris_merchant_receipt_name = fields.Char(string="Moneris Merchant Receipt Name",
                                                related="merchant_attachment_id.name")

    @api.depends('amount', 'payment_type', 'journal_id', 'moneris_cloud_receiptid', 'moneris_cloud_transid', 'state', 'moneris_refund_source_payment_id')
    def _compute_moneris_refund_balances(self):
        for record in self:
            record.moneris_refunded_amount = 0.0
            record.moneris_refundable_amount = 0.0

            if record.payment_type != 'inbound' or not record.moneris_cloud_receiptid:
                continue

            refunds = self.search([
                ('id', '!=', record.id),
                ('payment_type', '=', 'outbound'),
                ('state', '!=', 'cancel'),
                ('journal_id', '=', record.journal_id.id),
                ('moneris_refund_source_payment_id', '=', record.id)
            ])

            record.moneris_refunded_amount = sum(refunds.mapped('amount'))
            record.moneris_refundable_amount = max(record.amount - record.moneris_refunded_amount, 0.0)

    def _sync_moneris_refund_state(self):
        for record in self.filtered(lambda payment: payment.payment_type == 'inbound' and payment.moneris_cloud_receiptid):
            rounding = record.currency_id.rounding or 0.01
            record.is_moneris_refunded = float_is_zero(
                record.moneris_refundable_amount,
                precision_rounding=rounding,
            )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        source_payments = payments.mapped('moneris_refund_source_payment_id')
        if source_payments:
            source_payments._sync_moneris_refund_state()
        return payments
    def _send_moneris_request(self, values,is_moneris_go):
        moneris_service_name = 'moneris_cloud_go' if is_moneris_go else 'moneris_cloud'
        srm = AppPayment(service_name=moneris_service_name, service_type=values.get("service_type"),
                         service_key=values.get("token"))
        srm.data = values.get("data")
        response = srm.payment_process(company_id=self.company_id.id)
        _logger.info("moneris_validation response-->")
        if response.get("error"):
            response = {"error": True, "description": response.get("error")}
        elif response.get('errors_message'):
            response = {"error": True, "description": response.get('errors_message')}
        return response
    
    def action_get_receipt(self):
        _logger.info("action_get_receipt")
        pos_payment_method = self.env['pos.payment.method'].search([('journal_id','=',self.journal_id.id)], limit=1)
        if pos_payment_method:
            moneris_data = {
                "data": {"receiptType": "M",} if self._context["is_merchant"] else {},
                "service_type": "get_receipt",
                "token": pos_payment_method.token,


            }
            if pos_payment_method.moneris_device_id:
                moneris_data['data'].update({"terminal_id": pos_payment_method.cloud_terminal_id})
            try:
                response = self._send_moneris_request(values=moneris_data,is_moneris_go =pos_payment_method.is_moneris_go_cloud )
                _logger.info(response)
                if response.get("error"):
                    raise Exception(_(response.get("description")))
                else:
                    if response['receipt']['Error'] == "true":
                        raise UserError(_("Exception: %s") %
                                        response['receipt']['Message'])
                    else:
                        self.cloud_create_attachment(response, self._context["is_merchant"])
            except Exception as e:
                _logger.info("Exception occured %s", e)
                raise UserError(_("Exception occured: %s") % e)

    def cloud_create_attachment(self, resJson, is_merchant):

        file_content = resJson.get('receipt', {}).get('receipt') or resJson.get('receipt', {}).get('Receipt')
        _logger.info(resJson.get('receipt', {}).get('Receipt'))
        _logger.info("file_content %s", str(file_content))
        file_content = file_content[:46] + "%s\r\n%s\r\n%s\r\n" % (self.env.company.name, self.env.company.street,
                                                               self.env.company.city + ', ' + self.env.company.state_id.name + ' ' + self.env.company.zip) + file_content[46:]
        file = str(datetime.datetime.now().strftime("%m%d%Y%H%M%S%f"))
        folder_path = os.getenv("HOME") + "/mCloudFiles"
        if not os.path.isdir(folder_path):
            os.mkdir(folder_path)
        txt_name = folder_path + "/" + file + ".txt"
        pdf_name = folder_path + "/" + file + ".pdf"

        _logger.info("txt_name %s", str(txt_name))
        _logger.info("pdf_name %s", str(pdf_name))

        with open(txt_name, 'w') as f:
            f.write(file_content)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=15)
        f = open(txt_name, "r")
        for x in f:
            # pdf.cell(200, 10, txt = x, ln = 1, align = 'C')
            pdf.cell(200, 10, txt=x, ln=1)
        pdf.output(pdf_name)
        with open(pdf_name, "rb") as pdf_file:
            encoded_string = base64.b64encode(pdf_file.read())
        os.remove(txt_name)
        os.remove(pdf_name)
        file_name = "Merchant-" + self.moneris_cloud_txnname + "-" + self.moneris_cloud_transdate + ":" + self.moneris_cloud_transtime if is_merchant else self.moneris_cloud_txnname + "-" + self.moneris_cloud_transdate + ":" + self.moneris_cloud_transtime
        att = self.env['ir.attachment'].create({
            'name': file_name,
            'type': 'binary',
            'datas': encoded_string,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf'
        })
        if is_merchant:
            self.merchant_attachment_id = att.id
        else:
            self.attachment_id = att.id
        return True


    @api.depends('payment_type')
    def _compute_cloud_is_samecard(self):
        for record in self:
            record.cloud_is_samecard = False
            if record.payment_type == 'outbound' and record.payment_method_id.code == 'electronic' and \
                record.move_id.journal_id.use_cloud_terminal == True:
                inv_name = False
                if len(record.reconciled_invoice_ids) == 1:
                    inv_name = record.move_id.display_name.split("Reversal of: ")[1].split(",")[0].replace(")","")
                if len(record.reconciled_invoice_ids) > 1:
                    inv_name = record.move_id.display_name.split("(")[1].replace(")","")
                _logger.info("\ninv_name-->" + str(inv_name))
                domain = [('ref', 'like', inv_name),
                          ('payment_type', '=', 'inbound'),
                          ('moneris_last_digits', '=', record.moneris_last_digits)]
                payments = record.search(domain)
                _logger.info("\npayments, " + str(payments))
                if len(payments) > 0:
                    record.cloud_is_samecard = True

    @api.depends('moneris_last_digits')
    def _compute_reconciled_payment_ids(self):
        for record in self:
            record.has_payments = False
            record.reconciled_payments_count = 0
            if record.payment_type == 'inbound':
                domain = [('ref', 'like', record.ref),
                          # ('move_id.id','=',self.move_id.id),
                          ('payment_type', '=', 'outbound'),
                          ('moneris_last_digits', '=', record.moneris_last_digits)]
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
                  ('moneris_last_digits', '=', self.moneris_last_digits)]
        payments = self.search(domain)

        tree_view = self.env.ref('payment_moneris_cloud.account_payment_view_moneris')
        fomr_view = self.env.ref('account.view_account_payment_form')

        # if len(payments) == 1:
        #     action.update({
        #         'view_mode': 'form',
        #         'res_id': payments.id,
        #         'view_type': 'form',
        #     })
        # else:
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

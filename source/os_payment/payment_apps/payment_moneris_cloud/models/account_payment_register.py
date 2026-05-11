# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import random
import time

from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import logging
import pprint
import json
import pytz

from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)

def generate_idempotency_key():
    current_time_struct = time.localtime()
    timestamp_part = time.strftime("%Y%m%d%H%M%S", current_time_struct)
    random_part = random.randint(10, 99)
    idempotency_key = f"{timestamp_part}{random_part}"
    return idempotency_key


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    use_cloud_terminal = fields.Boolean(string="Use cloud terminal")
    support_mcloud_terminal = fields.Boolean()
    payment_type_inbound = fields.Boolean()
    payment_type_outbound = fields.Boolean()
    moneris_payment_status = fields.Selection(
        string='Payment Status',
        selection=[
            ('pending', 'Pending'),
            ('waiting', 'Waiting'),
            ('done', 'Done'),
            ('retry', 'Retry'),
            ('waitingCancel', 'Waiting Cancel'),
            ('reversing', 'Reversing'),
            ('reversed', 'Reversed'),
        ], default='pending'
    )
    moneris_move_name = fields.Char(compute='_onchange_journal_id')

    moneris_is_manual_payment = fields.Boolean(string="Is Manual Payment?", default=False)

    compute_domain_moneris_account_payment = fields.Binary(readonly=True,store=True)

    moneris_account_payment = fields.Many2one("account.payment",string="Moneris Account Payment" )

    moneris_refund_card_info = fields.Char(string="Moneris Payment Card info")
    moneris_refundable_amount = fields.Monetary(
        string="Moneris Refundable Amount",
        currency_field='currency_id',
        related='moneris_account_payment.moneris_refundable_amount',
        readonly=True,
    )

    moneris_device_id = fields.Many2one("moneris.device", ondelete='restrict',
        domain=lambda self: [('journal_id', '=', self.id)],)
    moneris_device_name = fields.Char(
        string='Moneris Device ID',
        related='moneris_device_id.code')

    @api.onchange('group_payment')
    def _onchange_group_payment(self):
        _logger.info("\n _onchange_group_payment")
        for rec in self:
            rec.moneris_move_name = ""
            if rec.group_payment == True and len(rec.line_ids.move_id) > 1:
                flag = False
                for line in rec.line_ids.move_id:
                    rec.moneris_move_name += line.name if flag == False else "," + line.name
                    flag = True

        _logger.info("\n--------------\n _onchange_group_payment: " + rec.moneris_move_name + "\n-----------")

    @api.onchange('journal_id')
    def _onchange_mn_journal_id(self):
        for rec in self:
            rec.moneris_move_name = ""
            _logger.info("\n _onchange_journal_id")
            if rec.group_payment == False and len(rec.line_ids.move_id) == 1:
                rec.moneris_move_name = rec.line_ids.move_id.name
            if rec.group_payment == True and len(rec.line_ids.move_id) > 1:
                flag = False
                for line in rec.line_ids.move_id:
                    rec.moneris_move_name += line.name if flag == False else "," + line.name
                    flag = True

            _logger.info("\n--------------\n _onchange_group_payment: " + rec.moneris_move_name + "\n-----------")

            print("use_cloud_terminal ===>>>", rec.journal_id.use_cloud_terminal)
            print("payment_type ===>>>", rec.payment_type)
            print("payment_type_inbound ===>>>", rec.payment_type_inbound)
            print("payment_type_outbound ===>>>", rec.payment_type_outbound)

            rec.use_cloud_terminal = rec.support_mcloud_terminal = rec.payment_type_inbound = False
            if rec.journal_id and rec.journal_id.use_cloud_terminal:
                rec.use_cloud_terminal = True
                rec.support_mcloud_terminal = True
                # if rec.payment_method_code == 'electronic':
                #     rec.support_mcloud_terminal = True
                #     if rec.payment_type == 'inbound':
                #         rec.payment_type_inbound = True
                #     if rec.payment_type == 'outbound':
                #         rec.payment_type_outbound = True

            print("*******************AFTER************************************")
            print("payment_type_inbound ===>>>", rec.payment_type_inbound)
            print("payment_type_outbound ===>>>", rec.payment_type_outbound)
            print("------------------------------------------------------------")

    @api.onchange('journal_id')
    def _onchange_account_payment_options(self):
        self.ensure_one()
        try:
            if self.journal_id.use_cloud_terminal:

                if self.env.context.get("active_model") == "account.move.line" and self.payment_type == 'outbound':

                    # active_move_id = self.env['account.move'].browse(self.env.context.get("active_ids"))
                    active_move_id = self.env['account.move'].search([('line_ids', 'in', self.env.context.get("active_ids"))])
                    source_move_id = active_move_id.reversed_entry_id
                    payment_values = source_move_id._get_reconciled_payments()
                    payment_ids = [i.id for i in payment_values.filtered(
                    lambda x: x.payment_type == 'inbound'
                    and x.journal_id.id == self.journal_id.id
                    and x.moneris_cloud_receiptid
                    and x.moneris_refundable_amount > 0)]
                    print(payment_ids)
                    if payment_ids:
                        self.moneris_account_payment = payment_ids[0]

                    self.compute_domain_moneris_account_payment = payment_ids

                    # return {
                    #     'domain': {
                    #         'moneris_account_payment': [('id', 'in', payment_ids), ("is_moneris_refunded", "=", False),
                    #                                     ("journal_id", "=", self.journal_id.id)]},
                    # }
            else:
                self.compute_domain_moneris_account_payment = False
        except:
            pass



    @api.onchange('moneris_account_payment')
    def _onchange_moneris_account_payment(self):
        self.ensure_one()
        try:
            if self.journal_id.use_cloud_terminal and self.env.context.get(
                    "active_model") == "account.move.line" and self.payment_type == 'outbound':
                refund_due_amount = abs(sum(self.line_ids.move_id.filtered(
                    lambda move: move.state == "posted"
                ).mapped("amount_residual_signed")))
                self.moneris_account_payment._compute_moneris_refund_balances()
                refundable_amount = self.moneris_account_payment.moneris_refundable_amount
                default_amount = refundable_amount
                if refund_due_amount:
                    default_amount = min(refund_due_amount, refundable_amount)

                if not self.amount:
                    self.amount = default_amount
                self.moneris_cloud_receiptid = self.moneris_account_payment.moneris_cloud_receiptid
                self.moneris_cloud_transid = self.moneris_account_payment.moneris_cloud_transid
                self.moneris_refund_card_info = (self.moneris_account_payment.moneris_cloud_cardname or "") + ":" + (
                            self.moneris_account_payment.moneris_cloud_pan[-4:] or "")

        except:
            pass


    moneris_cloud_receiptid = fields.Char(store=True)
    moneris_cloud_transid = fields.Char(store=True)

    # @api.onchange('journal_id')
    # def _compute_move_orderpay_moneris(self):
    #     for rec in self:
    #         if rec.journal_id.use_cloud_terminal == True and rec.payment_type == 'outbound':
    #             comm = rec.communication
    #             if comm:
    #                 inv_names = comm.split("Reversal of: ")
    #                 if len(inv_names) > 1:
    #                     inv_name = inv_names[1].split(",")[0]
    #                     _logger.info("inv_name--->" + inv_name)
    #                     AccPaymnt = self.env['account.payment']
    #                     pay_id = AccPaymnt.sudo().search(
    #                         [('move_id.memo', '=', inv_name)])
    #                     if pay_id:
    #                         rec.moneris_cloud_receiptid = pay_id.moneris_cloud_receiptid
    #                         rec.moneris_cloud_transid = pay_id.moneris_cloud_transid

    @api.onchange('amount')
    def _onchange_mn_amount(self):
        _logger.info("\n_onchange_journal_amt")
        for rec in self:

            amount_residual_signed = sum(
                rec.line_ids.move_id.filtered(lambda r: r.state == "posted").mapped("amount_residual_signed"))
            _logger.info("\namount_residual_signed: %.2f, amount: %.2f" % (amount_residual_signed, rec.amount))

            if rec.journal_id and rec.journal_id.use_cloud_terminal == True :

                # Invoice Payment Check
                if rec.payment_type == 'inbound' and rec.amount > amount_residual_signed:
                    raise UserError(_("You can not pay with this amount." + \
                                      "\nPayment Amount: %s%s,\nInvoice Due: %s %s" % (
                                      rec.currency_id.symbol, "{:.2f}".format(rec.amount), rec.currency_id.symbol,
                                      "{:.2f}".format(amount_residual_signed))))
                # Credit Note Payment Check
                if rec.payment_type == 'outbound' and rec.amount > abs(amount_residual_signed):
                    raise UserError(_("You can not refund with this amount." + \
                                      "\nPayment Amount: %s - %s,\nCredit Note Due Amount: %s %s" % (
                                      rec.currency_id.symbol, "{:.2f}".format(rec.amount), rec.currency_id.symbol,
                                      "{:.2f}".format(amount_residual_signed))))
                rec._validate_moneris_refund_amount_limit()

    def _validate_moneris_refund_amount_limit(self):
        for rec in self:
            if not (
                rec.journal_id.use_cloud_terminal
                and rec.use_cloud_terminal
                and rec.payment_type == 'outbound'
                and rec.moneris_account_payment
            ):
                continue

            refundable_amount = rec.moneris_account_payment.moneris_refundable_amount
            rounding = rec.currency_id.rounding or rec.moneris_account_payment.currency_id.rounding or 0.01
            if float_compare(rec.amount, refundable_amount, precision_rounding=rounding) > 0:
                raise UserError(_(
                    "Refund amount cannot be greater than the selected Moneris payment refundable amount."
                    "\nRefund Amount: %s %s"
                    "\nMoneris Refundable Amount: %s %s"
                ) % (
                    rec.currency_id.symbol,
                    "{:.2f}".format(rec.amount),
                    rec.currency_id.symbol,
                    "{:.2f}".format(refundable_amount),
                ))

    def _send_moneris_request(self, values,is_moneris_go):
        moneris_service_name = 'moneris_cloud_go' if is_moneris_go else 'moneris_cloud'
        srm = AppPayment(service_name=moneris_service_name, service_type=values.get("service_type"),
                         service_key=values.get("token"))
        srm.data = values.get("data")
        demo_data = self.env['ir.config_parameter'].sudo().get_param('moneris_clouddemo_data', 'False') == 'True'
        # if service_type == "refund":
        #     srm.data.update({
        #         "txn_number": datas.get('txnNumber')
        #     })
        if demo_data:
            response = {
              "receipt": {
                "apiVersion": "3.0",
                "dataId": "example_dataId",
                "statusCode": "5207",
                "status": "Approved",
                "dataTimestamp": "2025-07-21 16:47:24",
                "data": {
                  "response": [
                    {
                      "statusCode": "5207",
                      "status": "Approved",
                      "approvedAmount": "1388",
                      "totalAmount": "1110",
                      "cardType": "AX",
                      "cardName": "AMEX",
                      "sequenceNum": "006",
                      "realTimeUniqueId": "0SZROEX60D5XS84",
                      "responseCode": "025",
                      "iso": "00",
                      "authCode": "B41682",
                      "maskedPan": "***********1003",
                      "orderId": "124213xcsd",
                      "transactionId": "6-0_1201",
                      "idempotencyKey": "124213xcsdasde",
                      "action": "purchase",
                      "terminalId": "A2999074",
                      "saf": "false",
                      "tenderType": "Credit",
                      "formFactor": "00",
                      "tipAmount": "278",
                      "receiptChoice": "NONE",
                      "receipt": "     ------ TRANSACTION RECORD ------     \r\n                  TEST 1                  \r\n              3300 BLOOR ST               \r\n             ETOBICOKE    ON              \r\n\r\n                 Purchase                 \r\nJul 21,2025                       16:47:21\r\nAMEX                       ***********1003\r\n\r\nEntry: Tap EMV (H)                        \r\nRef#: 006-0SZROEX60D5XS84                 \r\nAuth#: B41682             Response: 00-025\r\nOrder:                          124213xcsd\r\n\r\nAmount                             $ 11.10\r\nTip                                 $ 2.78\r\n\r\nTotal                              $ 13.88\r\n\r\n\r\n\r\n\r\nA000000025010402 AMERICAN EXPRESS         \r\nTVR 8040008000                            \r\n\r\n                 Approved                 \r\nFF/DT 00                                  \r\n          Signature Not Required          \r\n\r\n\r\nImportant:Retain this copy for your record\r\n\r\n",
                      "completed": "true"
                    }
                  ]
                },
                "TxnName": "Purchase",
                "CloudTicket": "0394ab7d-3b12-4be4-ab20-d55b9d82c9ea",
                "Completed": "true",
                "Error": "true"
              }
            }
        else:
            response = srm.payment_process(company_id=self.company_id.id)

        _logger.info("moneris_validation response-->")
        _logger.info(response)
        # _logger.info(req)
        # _logger.info(req.text)
        # if req.status_code != 200:
        if response.get("error"):
            response = {"error": True, "description": response.get("error")}
        elif response.get('errors_message'):
            response = {"error": True, "description": response.get('errors_message')}
        return response


    def check_error_conditions(self):

        if not self.moneris_cloud_receiptid and not self.moneris_cloud_transid:
            raise UserError(_("No associate Payment Found!!"))
        self._validate_moneris_refund_amount_limit()

    def _create_payments(self):
        if self.journal_id.use_cloud_terminal and self.payment_type =="outbound":
            self.check_error_conditions()
        return super(AccountPaymentRegister, self)._create_payments()
            
        
    def _create_payment_vals_from_wizard(self,batch_result):
        res = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard(batch_result)
        try:
            journal = request.env['account.journal'].search(
                [('id', '=', res.get("journal_id"))])
            if journal.use_cloud_terminal:
                if not self.moneris_device_id:
                    raise UserError(_("Moneris Device is not selected...."))
                omni_sync_token = journal.token
                if res.get("payment_type") == "inbound":

                    moneris_val = {
                        "data": {
                            "order_id": res.get("memo"),
                            "amount": str(round(res.get("amount"), 2)),
                            "is_manual": self.moneris_is_manual_payment,
                        },
                        "service_type": "purchase",
                        "token": omni_sync_token
                    }
                elif res.get("payment_type") == "outbound":
                    self.check_error_conditions()
                    moneris_val = {
                        "data": {
                            "order_id": self.moneris_cloud_receiptid,
                            "amount": str(round(res.get("amount"), 2)),
                            "txn_number": self.moneris_cloud_transid,
                            "is_manual": self.moneris_is_manual_payment,

                        },
                        "service_type": "refund",
                        "token": omni_sync_token,

                    }

                if self.moneris_device_id:
                    moneris_val['data'].update({"terminal_id": self.moneris_device_name,"idempotency_key":generate_idempotency_key()})

                data = self._send_moneris_request(values=moneris_val,is_moneris_go = journal.is_moneris_go_cloud)
                if data.get("error") != True:
                    if not journal.is_moneris_go_cloud:
                        response = data.get("receipt")
                        if response.get('Error') == 'false' and (
                                response.get('ResponseCode') and int(response.get('ResponseCode')) < 50):
                            res.update({
                                "moneris_cloud_completed": response.get('Completed'),
                                "moneris_cloud_transtype": response.get('TransType'),
                                "moneris_cloud_error": response.get('Error'),
                                "moneris_cloud_initrequired": response.get('InitRequired'),
                                "moneris_cloud_safindicator": response.get('SafIndicator'),
                                "moneris_cloud_responsecode": response.get('ResponseCode'),
                                "moneris_cloud_iso": response.get('ISO'),
                                "moneris_cloud_languagecode": response.get('LanguageCode'),
                                "moneris_cloud_partailauthamount": response.get('PartialAuthAmount'),
                                "moneris_cloud_availablebalance": response.get('AvailableBalance'),
                                "moneris_cloud_tipamount": response.get('TipAmount'),
                                "moneris_cloud_emvcashbackamount": response.get('EMVCashBackAmount'),
                                "moneris_cloud_surchargeamount": response.get('SurchargeAmount'),
                                "moneris_cloud_foreigncurrencyamount": response.get('ForeignCurrencyAmount'),
                                "moneris_cloud_baserate": response.get('BaseRate'),
                                "moneris_cloud_exchangerate": response.get('ExchangeRate'),
                                "moneris_cloud_pan": response.get('Pan'),
                                "moneris_cloud_cardtype": response.get('CardType'),
                                "moneris_cloud_cardname": response.get('CardName'),
                                "moneris_cloud_accounttype": response.get('AccountType'),
                                "moneris_cloud_swipeindicator": response.get('SwipeIndicator'),
                                "moneris_cloud_formfactor": response.get('FormFactor'),

                                "moneris_cloud_cvmindicator": response.get('CvmIndicator'),
                                "moneris_cloud_reservedfield1": response.get('ReservedField1'),
                                "moneris_cloud_reservedfield2": response.get('ReservedField2'),
                                "moneris_cloud_authcode": response.get('AuthCode'),
                                "moneris_cloud_invoicenumber": response.get('InvoiceNumber'),
                                "moneris_cloud_emvechodata": response.get('EMVEchoData'),
                                "moneris_cloud_reservedfield3": response.get('ReservedField3'),
                                "moneris_cloud_reservedfield4": response.get('ReservedField4'),
                                "moneris_cloud_aid": response.get('Aid'),
                                "moneris_cloud_applabel": response.get('AppLabel'),
                                "moneris_cloud_apppreferredname": response.get('AppPreferredName'),
                                "moneris_cloud_arqc": response.get('Arqc'),
                                "moneris_cloud_tvrarqc": response.get('TvrArqc'),
                                "moneris_cloud_tcacc": response.get('Tcacc'),
                                "moneris_cloud_tvrtcacc": response.get('TvrTcacc'),
                                "moneris_cloud_tsi": response.get('Tsi'),
                                "moneris_cloud_tokenresponsecode": response.get('TokenResponseCode'),
                                "moneris_cloud_token": response.get('Token'),
                                "moneris_cloud_logonrequired": response.get('LogonRequired'),
                                "moneris_cloud_cncryptedcardinfo": response.get('EncryptedCardInfo'),
                                "moneris_cloud_transdate": response.get('TransDate'),
                                "moneris_cloud_transtime": response.get('TransTime'),
                                "moneris_cloud_amount": response.get('Amount'),
                                "moneris_cloud_referencenumber": response.get('ReferenceNumber'),
                                "moneris_cloud_receiptid": response.get('ReceiptId'),
                                "moneris_cloud_transid": response.get('TransId'),
                                "moneris_cloud_timeout": response.get('TimedOut'),
                                "moneris_cloud_cloudticket": response.get('CloudTicket'),
                                "moneris_cloud_txnname": response.get('TxnName')
                            })
                            # ======= Refund =============
                            if res.get("payment_type") == "outbound" and self.moneris_account_payment:
                                res["moneris_refund_source_payment_id"] = self.moneris_account_payment.id

                            return res
                        else:
                            if response.get('ResponseCode') and int(response.get('ResponseCode')) > 50:
                                raise Exception("Payment Declined!")
                            else:
                                if response.get("ErrorCode"):
                                    raise Exception(f"Payment Declined!")
                                raise Exception("Payment Incomplete!")
                    else:
                        receipt = data.get("receipt") or {}
                        response_list = (receipt.get("data") or {}).get("response") or []
                        response = response_list[0] if response_list else {}

                        def _pick(source, *keys):
                            for key in keys:
                                if key in source and source.get(key) is not None:
                                    return source.get(key)
                            return None

                        response_code = _pick(response, "ResponseCode", "responseCode")
                        response_status = _pick(response, "status") or _pick(receipt, "status")
                        try:
                            response_code_int = int(response_code) if response_code is not None else None
                        except (TypeError, ValueError):
                            response_code_int = None

                        is_approved = False
                        if response_code_int is not None:
                            is_approved = response_code_int < 50
                        elif response_status:
                            is_approved = str(response_status).lower() == "approved"

                        data_timestamp = _pick(receipt, "dataTimestamp")
                        trans_date = _pick(response, "TransDate")
                        trans_time = _pick(response, "TransTime")
                        if data_timestamp and (not trans_date or not trans_time):
                            parts = str(data_timestamp).split(" ")
                            if len(parts) >= 2:
                                trans_date = trans_date or parts[0]
                                trans_time = trans_time or parts[1]

                        if is_approved:
                            res.update({
                                "moneris_cloud_completed": _pick(response, "Completed", "completed") or _pick(receipt, "Completed"),
                                "moneris_cloud_transtype": _pick(response, "TransType", "action") or _pick(receipt, "TxnName"),
                                "moneris_cloud_error": _pick(response, "Error", "error") or _pick(receipt, "Error"),
                                "moneris_cloud_initrequired": _pick(response, "InitRequired"),
                                "moneris_cloud_safindicator": _pick(response, "SafIndicator", "saf"),
                                "moneris_cloud_responsecode": response_code,
                                "moneris_cloud_iso": _pick(response, "ISO", "iso"),
                                "moneris_cloud_languagecode": _pick(response, "LanguageCode"),
                                "moneris_cloud_partailauthamount": _pick(response, "PartialAuthAmount"),
                                "moneris_cloud_availablebalance": _pick(response, "AvailableBalance"),
                                "moneris_cloud_tipamount": _pick(response, "TipAmount", "tipAmount"),
                                "moneris_cloud_emvcashbackamount": _pick(response, "EMVCashBackAmount"),
                                "moneris_cloud_surchargeamount": _pick(response, "SurchargeAmount"),
                                "moneris_cloud_foreigncurrencyamount": _pick(response, "ForeignCurrencyAmount"),
                                "moneris_cloud_baserate": _pick(response, "BaseRate"),
                                "moneris_cloud_exchangerate": _pick(response, "ExchangeRate"),
                                "moneris_cloud_pan": _pick(response, "Pan", "maskedPan"),
                                "moneris_cloud_cardtype": _pick(response, "CardType", "cardType"),
                                "moneris_cloud_cardname": _pick(response, "CardName", "cardName"),
                                "moneris_cloud_accounttype": _pick(response, "AccountType"),
                                "moneris_cloud_swipeindicator": _pick(response, "SwipeIndicator"),
                                "moneris_cloud_formfactor": _pick(response, "FormFactor", "formFactor"),

                                "moneris_cloud_cvmindicator": _pick(response, "CvmIndicator"),
                                "moneris_cloud_reservedfield1": _pick(response, "ReservedField1"),
                                "moneris_cloud_reservedfield2": _pick(response, "ReservedField2"),
                                "moneris_cloud_authcode": _pick(response, "AuthCode", "authCode"),
                                "moneris_cloud_invoicenumber": _pick(response, "InvoiceNumber"),
                                "moneris_cloud_emvechodata": _pick(response, "EMVEchoData"),
                                "moneris_cloud_reservedfield3": _pick(response, "ReservedField3"),
                                "moneris_cloud_reservedfield4": _pick(response, "ReservedField4"),
                                "moneris_cloud_aid": _pick(response, "Aid"),
                                "moneris_cloud_applabel": _pick(response, "AppLabel"),
                                "moneris_cloud_apppreferredname": _pick(response, "AppPreferredName"),
                                "moneris_cloud_arqc": _pick(response, "Arqc"),
                                "moneris_cloud_tvrarqc": _pick(response, "TvrArqc"),
                                "moneris_cloud_tcacc": _pick(response, "Tcacc"),
                                "moneris_cloud_tvrtcacc": _pick(response, "TvrTcacc"),
                                "moneris_cloud_tsi": _pick(response, "Tsi"),
                                "moneris_cloud_tokenresponsecode": _pick(response, "TokenResponseCode"),
                                "moneris_cloud_token": _pick(response, "Token"),
                                "moneris_cloud_logonrequired": _pick(response, "LogonRequired"),
                                "moneris_cloud_cncryptedcardinfo": _pick(response, "EncryptedCardInfo"),
                                "moneris_cloud_transdate": trans_date,
                                "moneris_cloud_transtime": trans_time,
                                "moneris_cloud_amount": _pick(response, "Amount", "approvedAmount", "totalAmount"),
                                "moneris_cloud_referencenumber": _pick(response, "ReferenceNumber", "realTimeUniqueId", "sequenceNum"),
                                "moneris_cloud_receiptid": _pick(response, "ReceiptId", "orderId") or _pick(receipt, "dataId"),
                                "moneris_cloud_transid": _pick(response, "TransId", "transactionId"),
                                "moneris_cloud_timeout": _pick(response, "TimedOut"),
                                "moneris_cloud_cloudticket": _pick(response, "CloudTicket") or _pick(receipt, "CloudTicket"),
                                "moneris_cloud_txnname": _pick(response, "TxnName") or _pick(receipt, "TxnName")
                            })
                            # ======= Refund =============
                            if res.get("payment_type") == "outbound" and self.moneris_account_payment:
                                res["moneris_refund_source_payment_id"] = self.moneris_account_payment.id

                            return res
                        else:
                            if response_code_int is not None and response_code_int > 50:
                                raise Exception("Payment Declined!")
                            else:
                                if response_status and str(response_status).lower() != "approved":
                                    raise Exception("Payment Declined!")
                                if response.get("ErrorCode"):
                                    raise Exception(f"Payment Declined!")
                                raise Exception("Payment Incomplete!")
                else:
                    raise Exception(data.get("description"))
            else:
                return res


        except Exception as e:
            raise UserError(e)
            # raise UserError("Error")

    # @api.model
    # def action_create_payments(self, vals=None):
    #     _logger.info("action_create_payments----------------->")
    #     """Override account.payment.registe>>action_create_payments method
    #        This function writes moneris details on the account.payment record
    #     """
    #     res=

    #
    # record = self.browse(vals) if len(self) == 0 else self
    #
    # payments = record._create_payments()
    #
    # # ----------------------------------------------------------
    # if len(payments) > 0:
    #     _logger.info("payments-->" +str(payments))
    #     record._update_moneris_cloud_values(payments, record.env.context)
    #     # TO DO: Flush or Remove the Context
    #     try:
    #         context = record.env.context.copy()
    #         _logger.info("context ===>>>")
    #         context.update({'terminalResponse': False})
    #         record.env.context = context
    #     except Exception as e:
    #         _logger.info("Exception ===>>>" + str(e.args))
    #     try:
    #         context = request.env.context.copy()
    #         _logger.info("context ===>>>")
    #         context.update({'terminalResponse': False})
    #         request.env.context = context
    #     except Exception as e:
    #         _logger.info("Exception ===>>>" + str(e.args))
    #
    #
    # # ----------------------------------------------------------
    #
    # if record._context.get('dont_redirect_to_payments'):
    #     return True
    #
    # action = {
    #     'name': _('Payments'),
    #     'type': 'ir.actions.act_window',
    #     'res_model': 'account.payment',
    #     'context': {'create': False},
    # }
    # if len(payments) == 1:
    #     action.update({
    #         'view_mode': 'form',
    #         'res_id': payments.id,
    #     })
    # else:
    #     action.update({
    #         'view_mode': 'tree,form',
    #         'domain': [('id', 'in', payments.ids)],
    #     })
    # return action

    def _update_moneris_cloud_values(self, payments, context):
        """Function to update Moneris Cloud Values

        Args:
            payments ([dict]): Dict of Payment Values
            context (context): Request Context Values
        """
        if self.journal_id.use_cloud_terminal:
            if self.group_payment == True and len(self.line_ids.move_id) > 1:
                move_name = self.moneris_move_name or payments.memo

            if len(self.line_ids.move_id) == 1:
                move_name = self.moneris_move_name or payments.memo
                move_name = move_name.split(": ")[1] if ": " in move_name else move_name
                move_name = move_name.split(",")[0] if "," in move_name else move_name

            if context.get('terminalResponse'):

                _logger.info('\nTerminal Response\n' +
                             str(context.get('terminalResponse')))

                if len(payments) == 1:
                    tranRes = context.get('terminalResponse')
                    tranRes = json.loads(tranRes)

                    active_id = context.get('active_id') or context.get('active_ids')
                    accMove = request.env['account.move'].sudo().search(
                        [('id', '=', active_id)])

                    if len(accMove) > 0:
                        _logger.info("accMove ===>>> " + str(accMove) +
                                     "\n moneris_last_action ===>>> " + str(accMove[0].moneris_last_action))

                        action = 'PURCHASE'
                        if accMove[0].moneris_last_action == 'PURCHASE':
                            action = 'PURCHASE'
                        if accMove[0].moneris_last_action == 'REFUND':
                            action = 'REFUND'

                        # Response Different for Moneris Cloud
                        receipt = tranRes.get("receipt", {})
                        Completed = receipt.get("Completed")
                        card = receipt.get("card_type")

                        paidamt = payments.amount

                        if action == "REFUND" or action == "PURCHASE":
                            ter_amt = str(receipt.get("Amount"))

                        _logger.info(
                            "\n action--->" + str(action) +
                            "\n paidamt--->" + str(paidamt) +
                            "\n ter_amt--->" + str(ter_amt) +
                            "\n payments.memo--->" + str(payments.memo) +
                            "\n invoice_origin--->" + str(payments.invoice_origin) +
                            "\n invoice_name--->" + str(payments.move_id.name) +
                            "\n move_name--->" + str(move_name) +
                            "\n moneris_move_name--->" + str(self.moneris_move_name)
                        )

                        if payments.journal_id.use_cloud_terminal == True:
                            _logger.info(
                                "use_cloud_terminal--->" + str(payments.journal_id.use_cloud_terminal))
                            if paidamt == ter_amt:
                                _logger.info("Amount Matches")
                            if move_name != False:
                                if move_name in receipt.get('TransId'):
                                    _logger.info("transactionId Matches")

                            amt_tran = False
                            if paidamt == ter_amt and move_name in receipt.get('TransId'):
                                amt_tran = True

                            if len(self.line_ids.move_id) == 1:
                                if paidamt == ter_amt and \
                                        self.line_ids.move_id.display_name.split(" ")[0] in receipt.get('TransId'):
                                    amt_tran = True

                            if len(self.line_ids.move_id) > 1 and paidamt == ter_amt:
                                for move_id in self.line_ids.move_id:
                                    amt_tran = True if move_id.name in receipt.get('TransId') else False
                            print(amt_tran)
                            # ===========================
                            amt_tran = True
                            # ===========================
                            if amt_tran == True:
                                _logger.info("Amount and transactionId Matches")
                                # NEED TO CHECK VALUES
                                payment_vals = {
                                    'moneris_cloud_cloudticket': receipt.get('CloudTicket'),
                                    'moneris_cloud_receiptid': receipt.get('ReceiptId'),  # Important for REFUND
                                    'moneris_cloud_transid': receipt.get('TransId'),  # Important for REFUND
                                    'moneris_cloud_completed': receipt.get('Completed'),
                                    'moneris_cloud_transtype': receipt.get('TransType'),
                                    'moneris_cloud_error': receipt.get('Error'),
                                    'moneris_cloud_responsecode': receipt.get('ResponseCode'),
                                    'moneris_cloud_iso': receipt.get('ISO'),
                                    'moneris_cloud_pan': receipt.get('Pan'),
                                    'moneris_cloud_cardtype': receipt.get('CardType'),
                                    'moneris_cloud_accounttype': receipt.get('AccountType'),
                                    'moneris_cloud_cvmindicator': receipt.get('CvmIndicator'),
                                    'moneris_cloud_authcode': receipt.get('AuthCode'),
                                    'moneris_cloud_timeout': receipt.get('TimedOut'),
                                    'moneris_cloud_txnname': receipt.get('TxnName'),
                                    'moneris_cloud_transdate': receipt.get('TransDate'),
                                    'moneris_cloud_transtime': receipt.get('TransTime'),
                                }
                                if receipt.get('moneris_cloud_transtype') == 'Purchase':
                                    payment_vals['purchase_receipt_id'] = receipt.get('ReceiptId')
                                print(payment_vals)

                                payments.write(payment_vals)

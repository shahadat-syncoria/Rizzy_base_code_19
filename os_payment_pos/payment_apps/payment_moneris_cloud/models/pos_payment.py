# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import time

from odoo import models, fields, api, exceptions, _
import logging
from odoo.exceptions import UserError
import os
import datetime
import base64
import requests
from fpdf import FPDF
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)


class PosOrderPaymentInherit(models.Model):
    _inherit = 'pos.payment'

    def compute_pay_method(self):
        if self.payment_method_id.use_payment_terminal == 'moneris_cloud':
            self.is_moneris_cloud = True
        # This will be called every time the field is viewed

    is_moneris_cloud = fields.Boolean(string='Is Moneris Cloud', default=False)

    cloud_request_id = fields.Char("Cloud Request ID")
    purchase_cloud_ticket = fields.Char()
    payment_acquirer_name = fields.Char()
    purchase_receipt_id = fields.Char()
    # purchase_transaction_id = fields.Char()

    cloud_receipt_customer = fields.Text("Customer Receipt")
    cloud_receipt_merchant = fields.Text("Merchant Receipt")

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
    moneris_cloud_authcode = fields.Char("Auth Code ")
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
    moneris_cloud_token = fields.Char("Token ")
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
    moneris_card_type = fields.Char("Card Type ")

    is_moneriscloud_payment = fields.Boolean(
        default=False,
        compute='compute_is_moneriscloud_payment')

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

    @api.depends('payment_method_id')
    def compute_is_moneriscloud_payment(self):
        for record in self:
            record.is_moneriscloud_payment = False
            if record.payment_method_id.use_payment_terminal == 'moneris_cloud':
                record.is_moneriscloud_payment = True


    #Manually fetch Receipt 
    # [FIX]: Deprecated if not needed remove
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
        payment_method_id = self.payment_method_id

        moneris_data = {
            "data": {"receiptType": "M"} if self._context["is_merchant"] else {},
            "service_type": "get_receipt",
            "token": payment_method_id.token

        }
        if payment_method_id.moneris_device_id:
            moneris_data['data'].update({"terminal_id": payment_method_id.cloud_terminal_id})
        try:

            response = self._send_moneris_request(values=moneris_data,is_moneris_go=payment_method_id.is_moneris_go_cloud)
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

    
    
    
    # Fetch Receipt After POS Validate
    def cloud_create_attachment_customer(self):

        # file_content = resJson.get('receipt', {}).get('receipt') or resJson.get('receipt', {}).get('Receipt')
        if self.cloud_receipt_customer:
            file_content = self.cloud_receipt_customer
            final_receipt_br = file_content.replace('<br/>',"\r\n")
            file_content = final_receipt_br.replace('&nbsp'," ")
            # _logger.info(resJson.get('receipt', {}).get('Receipt'))
            _logger.info("file_content %s", str(file_content))
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
            if not self.moneris_cloud_transdate and not self.moneris_cloud_transtime:
                file_name = self.moneris_cloud_txnname + "-" + self.moneris_cloud_transid
            else:
                file_name =  self.moneris_cloud_txnname + "-" + (self.moneris_cloud_transdate or '') + ":" + (self.moneris_cloud_transtime or '')
            att = self.env['ir.attachment'].create({
                'name': file_name,
                'type': 'binary',
                'datas': encoded_string,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            # if is_merchant:
            #     self.merchant_attachment_id = att.id
            # else:
            self.attachment_id = att.id
            return True
    
    def cloud_create_attachment_merchant(self):

        # file_content = resJson.get('receipt', {}).get('receipt') or resJson.get('receipt', {}).get('Receipt')
        if self.cloud_receipt_merchant:
            file_content = self.cloud_receipt_merchant
            final_receipt_br = file_content.replace('<br/>',"\r\n")
            file_content = final_receipt_br.replace('&nbsp'," ")
            # _logger.info(resJson.get('receipt', {}).get('Receipt'))
            _logger.info("file_content %s", str(file_content))
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
            if not self.moneris_cloud_transdate and not self.moneris_cloud_transtime:
                file_name = "Merchant-" + self.moneris_cloud_txnname + "-" +  self.moneris_cloud_transid
            else:
                file_name = "Merchant-" + self.moneris_cloud_txnname + "-" + self.moneris_cloud_transdate + ":" + self.moneris_cloud_transtime
            att = self.env['ir.attachment'].create({
                'name': file_name,
                'type': 'binary',
                'datas': encoded_string,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            # if is_merchant:
            #     self.merchant_attachment_id = att.id
            # else:
            self.merchant_attachment_id = att.id
            return True

    # Only For POS Payment Receipt
    def _send_moneris_request_pos(self, values, payment_method_id):
        completed = False
        count = 0
        while not completed:
            moneris_service_name = 'moneris_cloud_go' if payment_method_id.is_moneris_go_cloud else 'moneris_cloud'
            srm = AppPayment(service_name=moneris_service_name, service_type=values.get("service_type"),
                             service_key=values.get("token"))
            srm.data = values.get("data")
            try:
                response = srm.payment_process(company_id=self.env.company.id,
                                               omni_account_id=payment_method_id.account_id.id)
                if 'receipt' in response:
                    # response["receipt"]["Completed"] ='false'
                    if response["receipt"]["Completed"] == 'true':
                        completed = True
                        break
                time.sleep(1)
                count += 1
                if count == 5:
                    break
            except Exception as e:
                pass

        # response = {'receipt': {'Completed': 'true', 'TransType': '58', 'Error': 'false', 'InitRequired': 'false', 'Receipt': '\r\n----------- TRANSACTION RECORD -----------\r\n\r\n                 Purchase                 \r\nDec 19,2022                       10:05:43\r\nINTERAC                   ************8644\r\nCHEQUING                                  \r\nTID: P1503106              Entry: Chip (C)\r\nSequence: 003                   Batch: 017\r\nAuth#: 430577             Response: 00-001\r\nUID: 1F2353363432083                      \r\n\r\nAmount                           $2,409.92\r\nTotal                            $2,409.92\r\nA0000002771010                            \r\nInterac                                   \r\nTVR 8080008000 TSI 6800                   \r\n           Approved - Thank You           \r\n             VERIFIED BY PIN              \r\n              MERCHANT COPY               \r\n', 'CloudTicket': 'c4e2dce2-ced2-455d-942a-df0881179ee7', 'TxnName': 'GetReceipt'}, 'error': None}
        _logger.info("moneris_validation Receipt response-->")
        if response.get("error"):
            response = {"error": True, "description": response.get("error")}
        elif response.get('errors_message'):
            response = {"error": True, "description": response.get('errors_message')}
        else:
            file_content = response.get("receipt").get("Receipt")
            file_content_final = file_content[:42] + "%s\r\n%s\r\n%s\r\n" % (
            self.env.company.name or '', self.env.company.street or '',
            self.env.company.city or '' + ', ' + self.env.company.state_id.name or '' if self.env.company.state_id else ''+ ' ' + self.env.company.zip or '') + file_content[
                                                                                                          46:]
            final_receipt_br = file_content_final.replace("\r\n", '<br/>')
            final_receipt = final_receipt_br.replace(" ",'&nbsp')


            response.get("receipt").update({
                'Receipt': final_receipt
            })

        return response

    def action_get_receipt_pos(self, **kwargs):
        _logger.info("action_get_receipt")
        p_m_id = self.env['pos.payment.method'].browse(kwargs['payment_method_id'])
        payment_method_id = p_m_id
        response_data = []
        for i in range(2):
            moneris_data = {
                "data": {"receiptType": "M"} if i == 1 else {},
                "service_type": "get_receipt",
                "token": payment_method_id.token

            }
            if p_m_id.moneris_device_id:
                moneris_data['data'].update({"terminal_id": p_m_id.cloud_terminal_id})
            try:

                response = self._send_moneris_request_pos(values=moneris_data,payment_method_id=payment_method_id)
                _logger.info(response)
                # if response.get("error"):
                #     # raise Exception(_(response.get("description")))
                #     _logger.error(_(response.get("description")))

                # else:
                #     if response['receipt']['Error'] == "true":
                #         # raise UserError(_("Exception: %s") %
                #         #                 response['receipt']['Message'])
                #         _logger.error(_("Exception: %s") %
                #                         response['receipt']['Message'])
                #     else:
                #         self.cloud_create_attachment(response,True if i==1 else False,kwargs['transaction_response'])
                response_data.append(response)
            except Exception as e:
                _logger.info("Exception occured %s", e)
                raise UserError(_("Exception occured: %s") % e)
        return response_data

    
    #[FIX ME]: Deprecated If not needed remove
    def cloud_create_attachment_pos(self, resJson, is_merchant,trasaction_response):

        file_content = resJson.get('receipt', {}).get('receipt') or resJson.get('receipt', {}).get('Receipt')
        _logger.info(resJson.get('receipt', {}).get('Receipt'))
        _logger.info("file_content %s", str(file_content))
        file_content = file_content[:46] + "%s\r\n%s\r\n%s\r\n" % (self.env.company.name or '', self.env.company.street or '',
                                                                   self.env.company.city or '' + ', ' + self.env.company.state_id.name or '' if self.env.company.state_id else '' + ' ' + self.env.company.zip or '') + file_content[
                                                                                                                                                                 46:]
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
        file_name = "Merchant-" + trasaction_response['TxnName'] + "-" + trasaction_response['TransDate'] + ":" + \
                    trasaction_response['TransTime'] if is_merchant else trasaction_response['TxnName'] + "-" + \
                                                                         trasaction_response['TransDate'] + ":" + \
                                                                         trasaction_response['TransTime']
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


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    payment_acquirer_name = fields.Char("Payment Acquirer Name")
    cloud_request_id = fields.Char("Cloud Request ID")
    purchase_receipt_id = fields.Char()

    moneris_cloud_cloudticket = fields.Char("Moneris Last Order Sequence")
    moneris_cloud_receiptid = fields.Char()
    moneris_cloud_transid = fields.Char()

    @api.model
    def _payment_fields(self, order, ui_paymentline):
        _logger.info("_payment_fields-->")
        _logger.info(order)
        from pprint import pprint
        pprint(ui_paymentline)

        fields = super(PosOrderInherit, self)._payment_fields(
            order, ui_paymentline)

        pay_method = self.env['pos.payment.method'].search(
            [('id', '=', int(ui_paymentline['payment_method_id']))])
        if pay_method != False:
            if pay_method.use_payment_terminal == 'moneris_cloud':
                fields.update({
                    'moneris_cloud_cloudticket': ui_paymentline.get('moneris_cloud_cloudticket'),
                    'moneris_cloud_receiptid': ui_paymentline.get('moneris_cloud_receiptid'),
                    'moneris_cloud_transid': ui_paymentline.get('moneris_cloud_transid'),
                    'moneris_cloud_completed': ui_paymentline.get('moneris_cloud_completed'),
                    'moneris_cloud_transtype': ui_paymentline.get('moneris_cloud_transtype'),
                    'moneris_cloud_error': ui_paymentline.get('moneris_cloud_error'),
                    'moneris_cloud_responsecode': ui_paymentline.get('moneris_cloud_responsecode'),
                    'moneris_cloud_iso': ui_paymentline.get('moneris_cloud_iso'),
                    'moneris_cloud_pan': ui_paymentline.get('moneris_cloud_pan'),
                    'moneris_cloud_cardtype': ui_paymentline.get('moneris_cloud_cardtype'),
                    'moneris_cloud_accounttype': ui_paymentline.get('moneris_cloud_accounttype'),
                    'moneris_cloud_cvmindicator': ui_paymentline.get('moneris_cloud_cvmindicator'),
                    'moneris_cloud_authcode': ui_paymentline.get('moneris_cloud_authcode'),
                    'moneris_cloud_timeout': ui_paymentline.get('moneris_cloud_timeout'),
                    'moneris_cloud_txnname': ui_paymentline.get('moneris_cloud_txnname'),
                    'cloud_receipt_customer': ui_paymentline.get('cloud_receipt_customer'),
                    'cloud_receipt_merchant': ui_paymentline.get('cloud_receipt_merchant'),
                    'moneris_cloud_transdate': ui_paymentline.get('moneris_cloud_transdate'),
                    'moneris_cloud_transtime': ui_paymentline.get('moneris_cloud_transtime'),
                })
                if ui_paymentline.get('moneris_cloud_transtype') == 'Purchase':
                    fields.update({'purchase_receipt_id': ui_paymentline.get('moneris_cloud_receiptid')})

        return fields

    # def add_payment(self, data):
    #     """Create a new payment for the order"""
    #     values = super(PosOrderInherit, self).add_payment(data)
    #     write_values = {}
    #     field_values = []
    #
    #     payments = self.payment_ids
    #
    #     if len(payments) > 0:
    #         if payments[0].payment_method_id.use_payment_terminal == 'moneris_cloud':
    #             for key, value in payments[0]._fields.items():
    #                 field_values.append(key)
    #
    #             for key, value in data.items():
    #                 if key in field_values:
    #                     write_values[key] = value
    #
    #             if (data.get('moneris_card_type') or data.get('card_type')) and not write_values.get(
    #                     'moneris_card_type'):
    #                 write_values['moneris_card_type'] = data.get('card_type')
    #             print("write_values")
    #             print(write_values)
    #             payments[0].write(write_values)
    #     return values

    def _process_payment_lines(self, pos_order, order, pos_session, draft):
        super(PosOrderInherit, self)._process_payment_lines(pos_order, order, pos_session, draft)
        if order.moneris_cloud_transid:
            moneris_payments = order.payment_ids.filtered_domain([("is_moneriscloud_payment", "=", True)])
            for payment in moneris_payments:
                payment.cloud_create_attachment_customer()
                payment.cloud_create_attachment_merchant()


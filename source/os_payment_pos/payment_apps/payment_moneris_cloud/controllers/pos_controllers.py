# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import http
from odoo.http import request
import json
import logging
import requests
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)

class MonerisCloudTerminal(http.Controller):

    @http.route('/moneriscloud/gettransaction', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def _get_urls(self, **kw):
        _logger.info("_get_urls")
        if 'transaction' in kw:
            if kw['transaction'] == '_sendTransaction':
                kw['error'] = False
                payment = request.env['pos.payment.method'].sudo().search([('id','=',int(kw['payment_method_id']))])
                if payment and payment.use_payment_terminal == 'moneris_cloud':
                    kw['use_payment_terminal'] = 'moneris_cloud'
                    kw['cloud_integration_method'] = payment.cloud_integration_method
                    kw['cloud_api_token'] = payment.cloud_api_token
                    kw['token'] = payment.token
                    kw['is_manual'] = payment.moneris_is_manual_payment
                    kw['cloud_postback_url'] = payment.cloud_postback_url
                    if payment.cloud_cloud_environment == 'test':
                        kw['cloud_inout_url'] = 'https://ippostest.moneris.com/Terminal'
                        kw['cloud_out_url1'] = 'https://iptermtest.moneris.com'
                        kw['cloud_out_url2'] = 'https://cloudreceiptct.moneris.com'
                    if payment.cloud_cloud_environment == 'enabled':
                        kw['cloud_inout_url'] = 'https://ippos.moneris.com'
                        kw['cloud_out_url1'] = 'https://ipterm.moneris.com'
                        kw['cloud_out_url2'] = 'https://cloudreceipt.moneris.com'
            else:
                kw['error']  = True
        from pprint import pprint
        pprint(kw)
        return json.dumps(kw)

    @http.route('/moneriscloud/validation', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_validation(self, **kw):
        _logger.info("moneris_validation")

        service_type = 'purchase'
        if kw['request_data']['txnType'] in ['refund']:
            print(kw)
            if kw.get('pos_order'):
                order = request.env['pos.order'].search([('pos_reference','=',kw.get('pos_order'))],limit=1)
                if order:
                    print(order.moneris_cloud_receiptid)
                    kw['request_data']['request']['orderId'] = order.moneris_cloud_receiptid
                    kw['request_data']['request']['txnNumber'] = order.moneris_cloud_transid
                    kw['request_data']['request']['is_manual'] = True
                    service_type='refund'
                    print(kw['request_data'])
                    if kw['request_data']['request']['orderId'] == False or kw['request_data']['request']['txnNumber'] == False:
                        print("EroorOrder id or txnNumber Misising")
                        req = {"error":True,"description":"Pos order Id cannot be empty. Please select order from Order list for refund"}
                        return json.dumps(req)
            else:
                req = {"error":True,"description":"Pos order Id cannot be empty. Please select order from Order list for refund"}
                from pprint import pprint
                pprint(req)
                return json.dumps(req)

        if kw['request_data']['txnType'] in ['purchase_correction']:
            service_type = "purchase_correction"

        URL = kw['result']['cloud_inout_url']
        if 'apiToken' not in kw['request_data']:
            kw['request_data']['apiToken'] = kw['result']['cloud_api_token']

        _logger.info("Final Validation Request----->")
        _logger.info(kw['request_data'])
       
        req = json.dumps(kw['request_data'])
        req = json.loads(req)
        datas = req.get("request")
        payment_method_id = kw['result']['payment_method_id'] if 'result' in kw else False

        service_name = 'moneris_cloud'
        if payment_method_id:
            pay_mt_id = request.env['pos.payment.method'].sudo().search([('id','=',int(payment_method_id))])
            if pay_mt_id.is_moneris_go_cloud:
                service_name = 'moneris_cloud_go'
        srm = AppPayment(service_name=service_name, service_type=service_type, service_key=kw['request_data']['token'])
        srm.data = {
                "order_id":datas.get('orderId'),
                "amount":datas.get('amount'),
                "is_manual": kw['result']['is_manual'],
        }
        if (service_name=='moneris_cloud_go'):
            srm.data.update({
                "idempotency_key": kw['request_data'].get('idempotencyKey')
            })
        if service_type == "refund" or kw['request_data']['txnType'] == "purchase_correction":
            srm.data.update({
                "txn_number": datas.get('txnNumber')
            })
        if kw['request_data'].get('terminalId'):
            srm.data.update({
                "terminal_id": kw['request_data'].get('terminalId')
            })

        response = srm.payment_process(company_id=kw['request_data']['company_id'])
        _logger.info(response)

        # response = {'receipt': {'Completed': 'true', 'TransType': '00', 'Error': 'false', 'InitRequired': 'false', 'SafIndicator': 'N', 'ResponseCode': '027', 'ISO': '01', 'LanguageCode': '5', 'PartialAuthAmount': None, 'AvailableBalance': None, 'TipAmount': 10.0, 'EMVCashBackAmount': None, 'SurchargeAmount': None, 'ForeignCurrencyAmount': None, 'ForeignCurrencyCode': None, 'BaseRate': None, 'ExchangeRate': None, 'Pan': '************4111', 'CardType': 'M ', 'CardName': 'MASTERCARD', 'AccountType': '4', 'SwipeIndicator': 'C', 'FormFactor': None, 'CvmIndicator': 'P', 'ReservedField1': None, 'ReservedField2': None, 'AuthCode': '863602', 'InvoiceNumber': None, 'EMVEchoData': None, 'ReservedField3': None, 'ReservedField4': None, 'Aid': 'A0000000041010', 'AppLabel': 'MASTERCARD', 'AppPreferredName': 'MasterCard', 'Arqc': 'A81BD7A3A2030B43', 'TvrArqc': '0400008000', 'Tcacc': '58DA77EFCDE114DB', 'TvrTcacc': '0400008000', 'Tsi': 'E800', 'TokenResponseCode': '00', 'Token': None, 'LogonRequired': 'N', 'EncryptedCardInfo': None, 'TransDate': '21-12-23', 'TransTime': '09:11:06', 'Amount': '42.30', 'ReferenceNumber': 'P15031060010010090', 'ReceiptId': 'Order 00007-001-0001/1', 'TransId': '505-0_20', 'TimedOut': 'false', 'CloudTicket': 'bf540469-34f5-45f6-9600-141db6fed05d', 'TxnName': 'Purchase'}, 'error': None}
        # if kw['request_data']['txnType'] == 'purchase_correction':
        #     response = {
        #     "receipt": {
        #         "Completed": "true",
        #         "TransType": "11",
        #         "Error": "false",
        #         "InitRequired": "false",
        #         "SafIndicator": "N",
        #         "ResponseCode": "027",
        #         "ISO": "01",
        #         "LanguageCode": "3",
        #         "PartialAuthAmount": None,
        #         "AvailableBalance": None,
        #         "TipAmount": None,
        #         "EMVCashBackAmount": None,
        #         "SurchargeAmount": None,
        #         "ForeignCurrencyAmount": None,
        #         "ForeignCurrencyCode": None,
        #         "BaseRate": None,
        #         "ExchangeRate": None,
        #         "Pan": "************2003",
        #         "CardType": "V ",
        #         "CardName": "VISA",
        #         "AccountType": "4",
        #         "SwipeIndicator": "C",
        #         "FormFactor": None,
        #         "CvmIndicator": "S",
        #         "ReservedField1": None,
        #         "ReservedField2": None,
        #         "AuthCode": "496204",
        #         "InvoiceNumber": None,
        #         "EMVEchoData": None,
        #         "ReservedField3": None,
        #         "ReservedField4": None,
        #         "Aid": "A0000000031010",
        #         "AppLabel": "VISA CREDIT",
        #         "AppPreferredName": None,
        #         "Arqc": None,
        #         "TvrArqc": None,
        #         "Tcacc": None,
        #         "TvrTcacc": None,
        #         "Tsi": None,
        #         "TokenResponseCode": None,
        #         "Token": None,
        #         "LogonRequired": "N",
        #         "EncryptedCardInfo": None,
        #         "TransDate": "18-02-13",
        #         "TransTime": "15:49:29",
        #         "Amount": "1.00",
        #         "ReferenceNumber": "610492970010140060",
        #         "ReceiptId": "example_orderId",
        #         "TransId": "example_txnNumber",
        #         "TimedOut": "false",
        #         "CloudTicket": "61ba1758-c1a5-4564-8bb8-841a409ea169",
        #         "TxnName": "PurchaseCorrection"
        #     }
        # }
        # req = requests.post(URL, json=req)
        _logger.info("moneris_validation response-->")
        # _logger.info(req)
        # _logger.info(req.text)
        # if req.status_code != 200:
        if response.get("error"):
            response = {"error":True,"description":response.get("error")}
        return json.dumps(response)

    @http.route('/moneriscloud/transaction', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_transaction(self, **kw):
        _logger.info("moneris_transaction---->")
        URL = kw['receiptUrl']
        _logger.info(URL)
        response = requests.get(URL)
        if response.status_code != 200:
            response = {"error":True, "description": "Error Code :" +  str(response.status_code)}
            return response
        else:
            response = response.json()
        _logger.info(response)
        return json.dumps(response)


    @http.route('/moneriscloud/getreceipt', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_receipt(self, **kw):
        _logger.info("moneris_transaction---->")
        response = request.env['pos.payment'].sudo().action_get_receipt_pos(payment_method_id=kw['payment_method_id'],
                                                                            transaction_response=kw[
                                                                                'transaction_resposnse'])

        return json.dumps(response)

    @http.route('/moneriscloud/get_order_info', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_get_order_info(self, **kw):
        _logger.info("moneris_transaction---->")
        pos_order_obj = request.env['pos.order']
        try:
            pos_order_id = pos_order_obj.sudo().search([('pos_reference', '=', kw.get('order_receipt_id'))], limit=1)
            response = {
                'moneris_cloud_receiptid': pos_order_id.moneris_cloud_receiptid,
                'moneris_cloud_transid': pos_order_id.moneris_cloud_transid
            }
        except Exception as e:
            response = {
                'moneris_cloud_receiptid': False,
                'moneris_cloud_transid': False
            }
            _logger.warning(f"Error:{e}")

        return json.dumps(response)
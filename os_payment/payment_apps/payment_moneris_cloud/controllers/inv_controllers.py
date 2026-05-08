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
import random
import string

_logger = logging.getLogger(__name__)


class MonerisCloudInvoice(http.Controller):

    @http.route('/moneriscloudinv/gettransaction', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def _get_inv_urls(self, **kw):
        _logger.info("/moneriscloudinv/gettransaction ===>>>>")
        if 'transaction' in kw:
            if kw['transaction'] == '_sendTransaction':
                kw['error'] = False
                journal = request.env['account.journal'].sudo().search(
                    [('id', '=', int(kw['journal_id']))])
                move_id = request.env['account.move'].sudo().search(
                    [('id', '=', int(kw['move_id']))])
                if journal and journal.use_cloud_terminal:
                    kw['use_cloud_terminal'] = 'moneris_cloud'
                    kw['cloud_integration_method'] = journal.cloud_integration_method
                    kw['cloud_api_token'] = journal.cloud_api_token
                    kw['cloud_postback_url'] = journal.cloud_postback_url
                    if journal.cloud_cloud_environment == 'test':
                        kw['cloud_inout_url'] = 'https://ippostest.moneris.com/Terminal'
                        kw['cloud_out_url1'] = 'https://iptermtest.moneris.com'
                        kw['cloud_out_url2'] = 'https://cloudreceiptct.moneris.com'
                    if journal.cloud_cloud_environment == 'enabled':
                        kw['cloud_inout_url'] = 'https://ippos.moneris.com'
                        kw['cloud_out_url1'] = 'https://ipterm.moneris.com'
                        kw['cloud_out_url2'] = 'https://cloudreceipt.moneris.com'
            else:
                kw['error'] = True
        from pprint import pprint
        pprint(kw)
        return json.dumps(kw)

    @http.route('/moneriscloudinv/validation', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_inv_validation(self, **kw):
        _logger.info("/moneriscloudinv/validation ===>>>>")
        href = kw.get('href')
        href_dict = {}
        journal_id = False
        if href and '#' in href:
            href_list = href.split('#')[1].split('&')
            for params in href_list:
                href_dict[params.split('=')[0]] = params.split('=')[1]
            
        if href_dict.get('model') == 'account.move':
            kw['move_id'] = href_dict.get('id')

        print("href_dict ===>>>", href_dict)
        print("journal_id ===>>>>", kw.get('journal_id'))
        

        if kw.get('journal_id') :
            journal = request.env['account.journal'].search(
                [('id', '=', int(kw.get('journal_id')))])
            print("journal ===>>>>", journal)
            if len(journal) > 0:
                journal._compute_urls()
                if journal.cloud_cloud_environment == 'test':
                    journal.cloud_inout_url = 'https://ippostest.moneris.com/Terminal/'
                    journal.cloud_out_url1 = 'https://iptermtest.moneris.com'
                    journal.cloud_out_url2 = 'https://cloudreceiptct.moneris.com'
                if journal.cloud_cloud_environment == 'enabled':
                    journal.cloud_inout_url = 'https://ippos.moneris.com/Terminal/'
                    journal.cloud_out_url1 = 'https://ipterm.moneris.com'
                    journal.cloud_out_url2 = 'https://cloudreceipt.moneris.com'


                kw['result']['cloud_inout_url'] = journal.cloud_inout_url
        if kw['request_data']['txnType'] == 'refund':
            pass

        URL = kw['result']['cloud_inout_url']
        if 'apiToken' not in kw['request_data']:
            kw['request_data']['apiToken'] = kw['result']['cloud_api_token']

        _logger.info("Final Validation Request----->")
        _logger.info(kw['request_data'])

        req = json.dumps(kw['request_data'])
        req = json.loads(req)
        req = requests.post(URL, json=req)
        _logger.info("moneris_validation response-->")
        _logger.info(req)
        _logger.info(req.text)
        if req.status_code != 200:
            response = {"error": True, "description": req.status_code}
        else:
            response = req.text
        return json.dumps(response)


    @http.route('/moneriscloudinv/transaction', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_transaction(self, **kw):
        _logger.info("/moneriscloudinv/transaction ===>>>>")
        URL = kw['receiptUrl']
        _logger.info(URL)
        response = requests.get(URL)
        if response.status_code != 200:
            response = {
                "error": True, "description": "Error Code :" + str(response.status_code)}
            return response
        else:
            response = response.json()
        _logger.info(response)
        return json.dumps(response)

    @http.route('/monerisinv/moneris_records', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def moneris_records(self, **kw):
        AccJournal = request.env['account.journal'].sudo()
        AccMove = request.env['account.move'].sudo()
        ApRegister = request.env['account.payment.register'].sudo()
        PaymentMethod = request.env['account.payment.method'].sudo()

        print("journal_id ===>>>>", kw.get('journal').get('journal_id'))

        if kw.get('journal').get('journal_id'):
            journal = AccJournal.search(
                [('id', '=', int(kw.get('journal').get('journal_id')))])
            if len(journal) > 0:
                kw['journal'].update({
                    'use_cloud_terminal': journal.use_cloud_terminal,
                    'cloud_store_id': journal.cloud_store_id,
                    'cloud_api_token': journal.cloud_api_token,
                    'cloud_terminal_id': journal.cloud_terminal_id,

                    'cloud_pairing_token': journal.cloud_pairing_token,
                    'cloud_postback_url': journal.cloud_postback_url,
                    'cloud_integration_method': journal.cloud_integration_method,
                    'cloud_cloud_environment': journal.cloud_cloud_environment,
                    'cloud_cloud_paired': journal.cloud_cloud_paired,
                    'cloud_cloud_ticket': journal.cloud_cloud_ticket,
                    'cloud_inout_url': journal.cloud_inout_url,
                    'cloud_out_url1': journal.cloud_out_url1,
                    'cloud_out_url2': journal.cloud_out_url2,
                    'cloud_merchant_id': journal.cloud_merchant_id,
                })

        if kw.get('move').get('move_ids'):
            move_ids = kw.get('move').get('move_ids')
            if type(move_ids) == int:
                move_ids = [move_ids]
            moves = AccMove.search([('id', 'in', move_ids)])

            moves_arr = []
            move_names = ''
            flag = False
            for move in moves:
                moves_arr.append({
                    'moneris_request_id': move.moneris_request_id or None,
                    'moneris_last_action': move.moneris_last_action or None,
                    'moneris_transaction_id': move.moneris_transaction_id or None,
                    'moneris_idempotency_key': move.moneris_idempotency_key or None,
                    'name': move.name or None,
                    'amount': move.amount_residual_signed or None,

                })
                move_names += move.name if flag == False else "," + move.name
                flag = True

            kw['moves_arr'] = moves_arr
            kw['move_names'] = move_names

            if len(moves) > 1:
                kw['move'].update({
                    'moneris_request_id': move.moneris_request_id or None,
                    'moneris_last_action': move.moneris_last_action or None,
                    'moneris_transaction_id': move.moneris_transaction_id or None,
                    'moneris_idempotency_key': move.moneris_idempotency_key or None,
                    'name': move_names,  # move.name or None,
                    'amount': move.amount_residual_signed or None,

                })

        if kw.get('register').get('register_id'):
            register_id = kw.get('register').get('register_id').split("_")[1]
            register = ApRegister.search([('id', '=', int(register_id))])
            if len(register) > 0:
                kw['register'].update({
                    'amount': register.amount,
                    'journal_id': str(register.journal_id.id),
                    'payment_date': str(register.payment_date),
                    'communication': register.communication,
                    'creation_date': str(register.payment_date),
                })

        if kw.get('payment_method').get('payment_method_id'):
            pm_id = kw.get('payment_method').get('payment_method_id')
            pm = PaymentMethod.search([('id', '=', pm_id)])
            if len(pm) > 0:
                kw['payment_method'].update({
                    'code': pm.code,
                    'payment_type': pm.payment_type,
                    'name': pm.name,
                })

        print("kw")
        print(kw)
        return kw

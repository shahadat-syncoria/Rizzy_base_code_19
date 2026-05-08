# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests, json
import pprint
from ..models.clover_request import CloverRequest

from odoo import http, _
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

class CloverWebhookUrl(http.Controller):

    @http.route('/pos/order/payment', type='jsonrpc', auth="none", methods=['POST'], csrf=False)
    def orderpayment(self, **post):
        _logger.info("\npost\n" + pprint.pformat(post))
        res = {}
        if post.get('pos_reference'):
            order_name = post.get('pos_reference')
            pos_order_id = request.env['pos.order'].sudo().search([('pos_reference', '=', order_name)])
            if pos_order_id:
                payment = request.env['pos.payment'].sudo().search([('pos_order_id', '=', pos_order_id.id)])
                if payment:
                    res = {
                        'clover_order_id': payment.clover_order_id,
                        'clover_payment_id': payment.clover_payment_id,
                    }

        _logger.info("res" + str(res))

        if post.get('headers') and post.get('payload'):
            headers = post.get('headers', {})

            if headers.get('Authorization'):
                post['headers']['Authorization'] = headers['Authorization']
            res = self.action_send_clover_payment(post)
        return res

    def action_send_clover_payment(self, values):
        clover_payment = {'success': False}

        if values.get('clover_order_id') and values.get('payment_method_id') and values.get('order_name'):
            payment_method_id = request.env['pos.payment.method'].sudo().browse(int(values.get('payment_method_id')))
            if payment_method_id.use_payment_terminal == 'clover_cloud':
                payload = values['payload']
                payload.update({
                    'payment_method_id': payment_method_id,
                    'cloverJwtToken': payment_method_id.clover_jwt_token,
                    'cloverServerUrl': payment_method_id.clover_server_url,
                })
                cpr = CloverRequest(debug_logger=True, values=payload)
                clover_payment = cpr.action_send_clover_payment(values=payload)

        return clover_payment

    @http.route('/clover/webhook/', type='jsonrpc', auth='public', csrf=False, methods=['POST'], cors='*')
    def clover_webhook(self, s_action=None, db=None, **kw):
        data = json.loads(request.httprequest.data)
        _logger.info("DATA\n" + pprint.pformat(data))
        self.update_webhook_code(data)

    def update_webhook_code(self, data):
        PosPayMthd = request.env['pos.payment.method'].sudo()
        clover_id = False
        if data.get("verificationCode"):
            try:
                domain = [('use_payment_terminal', '=', 'clover_cloud')]
                clover_id = PosPayMthd.search(domain, order='id desc', limit=1)
                if clover_id:
                    _logger.info("clover_id-->" + str(clover_id))
                    clover_id.write(
                        {"clover_wbhk_actcode": data.get("verificationCode")})
                    message = "Clover Webbook updated with Code: %s" % (
                        str(data.get("verificationCode")))
                else:
                    message = "No Payment Method for Clover Found"
                response = True
            except Exception as e:
                message = _("Update Webhook Error: " + str(e.args))
                _logger.warning(message)
                response = False

            log_vals = {
                "func": "update_webhook_code",
                "line": "35",
                "message": message,
                "name": "CloverWebhookUrl",
                "path": "/clover/webhook/",
                "type": "server",
                "level": "info",
                "payment_method_id": clover_id.id,
            }
            self.create_logging(log_vals)

        return {"response": response}

    def create_logging(self, log_vals):
        _logger.info("create_logging")
        IrLog = request.env['ir.logging'].sudo()
        log_id = IrLog.create(log_vals)
        _logger.info("Log-%s" % (log_id))

    @http.route(['/clover/authrcv', '/clover/authrcv/oauth_callback'], type='http', auth="public", website=True)
    def cloverauthrcv(self, s_action=None, db=None, **kw):
        PosPayMthd = request.env['pos.payment.method'].sudo()
        # https://www.example.com/oauth_callback?merchant_id={mId}&employee_id={employeeId}&client_id={client_id}&code={AUTHORIZATION_CODE}
        _logger.info("\ncloverauthrcv kw\n" + pprint.pformat(kw))
        merchant_id = kw.get('merchant_id')  # mId
        employee_id = kw.get('employee_id')  # employeeId
        client_id = kw.get('client_id')  # client_id
        AUTHORIZATION_CODE = kw.get('code')  # client_id

        if AUTHORIZATION_CODE:
            domain = [
                ('use_payment_terminal', '=', 'clover_cloud'),
                ('clover_merchant_id', '=', merchant_id),
            ]
            clover_id = PosPayMthd.search(domain, order='id desc', limit=1)
            if clover_id:
                """Update the Authrization Code"""
                clover_id.write({'clover_auth_code': AUTHORIZATION_CODE})
                message = "clover_id %s updated with AUTHORIZATION_CODE" % (
                    clover_id)
                _logger.info(message)
                log_vals = {
                    "func": "Clover Authorization Code ",
                    "line": "35",
                    "message": message,
                    "name": "CloverWebhookUrl",
                    "path": "/clover/authrcv",
                    "type": "server",
                    "level": "info",
                    "payment_method_id": clover_id.id,
                }
                kw.update({'clover_id': clover_id})
                self.create_logging(log_vals)

        return request.render("odoo_clover_cloud.clover_auth_rcv", {'context': kw})

    @http.route('/clover/updateflag', type='jsonrpc', auth='public', methods=['POST'], website=True, csrf=False)
    def updateflag(self, **kw):
        _logger.info("\nupdateflag---->\n" + pprint.pformat(kw))
        res = {}
        model = kw.get('model')
        PosPayMthd = request.env['pos.payment.method'].sudo()
        AccJournal = request.env['account.journal'].sudo()
        pay_mthd_id = kw.get('id') or False
        journal_id = kw.get('journal_id') or False

        if model == 'pos.payment.method':
            pay_mthd_id = PosPayMthd.search(
                [('use_payment_terminal', '=', 'clover_cloud')], order='id desc', limit=1)
        if model == 'account.journal':
            journal_id = AccJournal.browse(int(journal_id))
            # if pay_mthd_id:
        #     pay_mthd_id.write({'clover_cloud_paired': True})
        if journal_id:
            journal_id.write({'clover_cloud_paired': True})

        log_vals = {
            "func": kw.get('function') or "Clover Pairing",
            "line": "125",
            "message": kw.get('message'),
            "name": kw.get('name', "CloverWebhookUrl"),
            "path": "/clover/updateflag",
            "type": "server",
            "level": "info",
            # "payment_method_id": pay_mthd_id.id if kw.get('id') else False,
            # "journal_id": journal_id.id,

        }
        self.create_logging(log_vals)
        res = {'success': 'true', 'description': kw.get('message')}
        return res

    @http.route('/cloverinv/clover_records', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def clover_records(self, **kw):
        AccJournal = request.env['account.journal'].sudo()
        AccMove = request.env['account.move'].sudo()
        ApRegister = request.env['account.payment.register'].sudo()
        PaymentMethod = request.env['account.payment.method'].sudo()

        if kw.get('journal').get('journal_id'):
            journal = AccJournal.search(
                [('id', '=', int(kw.get('journal').get('journal_id')))])
            if len(journal) > 0:
                kw['journal'].update({
                    'use_clover_terminal': journal.use_clover_terminal,
                    'clover_application_id': journal.clover_application_id,
                    'clover_app_secret': journal.clover_app_secret,
                    'clover_merchant_id': journal.clover_merchant_id,
                    'clover_access_token': journal.clover_access_token,
                    'clover_device_id': journal.clover_device_id,
                    'clover_device_name': journal.clover_device_name,
                    'clover_server': journal.clover_server,
                    'clover_friendly_id': journal.clover_friendly_id,
                    'state': journal.state,
                    'clover_region': journal.clover_region,
                    'clover_cloud_paired': journal.clover_cloud_paired,
                    'clover_accept_signature': journal.clover_accept_signature,
                    'clover_wbhk_actcode': journal.clover_wbhk_actcode,
                    'clover_wbhk_url': journal.clover_wbhk_url,
                    'clover_auth_code': journal.clover_auth_code,
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
                    'name': move.name or None,
                    'amount': move.amount_residual_signed or None,

                })
                move_names += move.name if flag == False else "," + move.name
                flag = True

            kw['moves_arr'] = moves_arr
            kw['move_names'] = move_names

            if len(moves) > 1:
                kw['move'].update({
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

        _logger.info("\nkw\n" + pprint.pformat(kw))
        return kw

    @http.route('/clovercloud/get_order_info', type='jsonrpc', auth='user', csrf=False, methods=['POST'])
    def clover_get_order_info(self, **kw):
        _logger.info("clover_transaction---->")
        pos_order_payment_obj = request.env['pos.payment']
        try:
            pos_order_payment_id = pos_order_payment_obj.sudo().search([('pos_order_id.id', '=', kw.get('order_id'))], limit=1)
            response = {
                'clover_request_id': pos_order_payment_id.clover_payment_id,
                'clover_ext_payment_ids': pos_order_payment_id.clover_payment_id
            }
        except Exception as e:
            response = response = {
                'clover_request_id': False,
                'clover_ext_payment_ids': False
            }
            _logger.warning(f"Error:{e}")

        return json.dumps(response)

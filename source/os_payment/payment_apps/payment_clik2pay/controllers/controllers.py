# -*- coding: utf-8 -*-

import base64
import binascii
import hashlib
import hmac
import logging
import pprint
import re

from werkzeug import urls
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

import requests
import json
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)

def remove_charandaccents(string):
    if string != None:
        return re.sub(r'[^ \nA-Za-z0-9/]+', '', string)
    else:
        return ''


class Clik2PayWebhookController(http.Controller):
    _webhook_url = '/payment/clik2pay/notification'
    _payment_url = '/payment/clik2pay/payment'

    @http.route(_webhook_url, type='jsonrpc', auth='public', methods=['POST'])
    def clik2pay_webhook(self, **post):
        # Parse the JSON data from the webhook
        json_data = json.loads(request.httprequest.data)

        # Extract the relevant data from the JSON payload
        resource_id = json_data['resource']['id']
        event_type = json_data['eventType']
        message = json_data['message']
        resource_type = json_data['resourceType']
        invoice_number = json_data['resource'].get('invoiceNumber', '')
        payment_method = json_data['resource'].get('paymentMethod', '')
        

        # Create a new record in the clik2pay.webhook.log model
        request.env['clik2pay.webhook.log'].sudo().create({
            'resource_id': resource_id,
            'event_type': event_type,
            'message': message,
            'resource_type': resource_type,
            'invoice_number': invoice_number,
            'payment_method': payment_method,
            'json_data': json.dumps(json_data)
        })

        # Add the Odoo URL to the JSON data
        # odoo_url = request.httprequest.base_url 
        # json_data['odoo_url'] = odoo_url.replace(self._webhook_url, '')

        # Post the JSON data to the specified external URL
        # webhook_url = 'https://webhook.site/894e7fcd-bf81-4810-8530-57ce567ac3d7'
        webhook_url =  request.env['ir.config_parameter'].sudo().get_param('clik2pay.clik2pay_webhook_urls')
        if webhook_url and webhook_url != 'True':
            headers = {'Content-Type': 'application/json'}
            print(f"Request gone to =============>{webhook_url}")
            response = requests.post(webhook_url, data=json.dumps(json_data), headers=headers)
            print(f"Request success to =============>{str(response)}")

        # Process notification data
        data = request.dispatcher.jsonrequest
        _logger.info('notification data', data)
        _logger.info("DATE coming ==========>>>>>>"+json.dumps(data))
        try:
            # Check the integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'clik2pay', data
            )
            tx_sudo._process('clik2pay', data)
        except ValidationError:
            # Warn rather than log the traceback to avoid noise when a POS payment notification
            # is received and the corresponding `payment.transaction` record is not found.
            _logger.warning("unable to find the transaction; skipping to acknowledge")

        return '[accepted]'  # Acknowledge the notification

    
    @http.route(_payment_url, type='jsonrpc', auth='public')
    def send_payment(self, reference, provider_id, currency_id, access_token, converted_amount, partner_id):
        # Make the payment request to Clik2Pay
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()

        # Check that the transaction details have not been altered. This allows preventing users
        # from validating transactions by paying less than agreed upon.
        if provider_sudo and provider_sudo.clik2pay_tampered_payment:
            if not payment_utils.check_access_token(
                    access_token, reference, converted_amount, partner_id
            ):
                raise ValidationError("Clik2Pay: " + ("Received tampered payment request data."))

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        # data['memo'] = "Odoo " + service.common.exp_version()['server_version']
        currency = request.env['res.currency'].sudo().browse(currency_id).name
        partner = request.env['res.partner'].sudo().browse(partner_id)

        # Check if the partner already has a merchantAccountId, if not, generate and set it
        if not partner.merchantAccountId:
            partner.write({
                'merchantAccountId': partner._generate_merchant_account_id()
            })

        data = {
            "type": "ECOMM",
            "payer": {
                "name": remove_charandaccents(partner.name),
                "merchantAccountId": partner.merchantAccountId,
                "email": partner.email,
                "mobileNumber": partner.phone.replace(' ', '').replace('-', '').replace('+1', ''),
                "preferredLanguage": "en"
            },
            # "flexDetails": {
            #     "requested": float(converted_amount),
            #     "minimum": float(converted_amount),
            #     "maximum": float(converted_amount) 
            # },
            "amount": float(converted_amount),
            "invoiceNumber": reference
        }

        response = None
        try:
            # r = provider_sudo._clik2pay_make_request(
            #     endpoint='payment-requests',
            #     payload=json.dumps(data),
            #     method='POST'
            # )
            response = provider_sudo._clik2pay_make_request('payment_request',payload=data)

            # Handle the payment request response
            _logger.info("payment request response: %s", pprint.pformat(response))

            # if the merchantOrderId already exists in clik2pay and you try to pay again, the createInvoice return
            # So her we check, if he response is string thne
            if isinstance(response, str):
                tx_sudo._set_error(response)
                raise ValidationError(
                    "clik2pay: " + "Create Invoice response %(ref)s.", ref=response
                )
            tx_sudo.write({
                'provider_reference': response.get('invoiceNumber'),
                'clik2pay_reference': response.get('id'),
                'clik2pay_merchant_transaction_id': response.get('merchantTransactionId'),
                'clik2pay_merchant_id': response['merchant'].get('id')
            })
            return json.dumps(response)
        except requests.exceptions.RequestException:
            _logger.exception("Error wit Clik2Pay service %s", json.dumps(response))
            raise ValidationError(
                "Detail: " + response.get('detail', ("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", str(e))
            raise ValidationError(str(e))
    
    @http.route('/payment/clik2pay/status', type='jsonrpc', auth='public')
    def get_payment_status(self, token, provider_id, bypass_webhook_check=False):
        try:
            if bypass_webhook_check:
                # When bypass_webhook_check is True, call the _clik2pay_make_request method directly
                provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
                payload = {
                    'payment_request_id': token
                }
                response = provider_sudo._clik2pay_make_request('get_payment_request_status', payload=payload, method='GET')
            else:
                # When bypass_webhook_check is False, check the webhook log
                webhook_log = request.env['clik2pay.webhook.log'].sudo().search([('resource_id', '=', token)])
                if webhook_log:
                    if webhook_log.event_type == 'PAYMENT-COMPLETED' or webhook_log.event_type == 'PAYMENT-FAILED':
                        # If the event type is PAYMENT-COMPLETED or PAYMENT-FAILED, call the Clik2Pay API
                        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
                        payload = {
                            'payment_request_id': token
                        }
                        response = provider_sudo._clik2pay_make_request(f'get_payment_request_status', payload=payload, method='GET')
                    else:
                        response = {'status': 'pending'}

            if response:
                event_code = response.get('status')
                if event_code == 'ACTIVE':
                    return json.dumps({'status': 'active'})
                elif event_code == 'CREATED' or event_code == 'SCHEDULED':
                    return json.dumps({'status': 'pending'})
                elif event_code == 'PAID' or event_code == 'SETTLED':
                    return json.dumps({'status': 'completed'})
                elif event_code == 'FAILED':
                    return json.dumps({'status': 'failed'})
                elif event_code == 'CANCELLED':
                    return json.dumps({'status': 'canceled'})
                else:
                    return json.dumps({'status': 'pending'})
            else:
                return json.dumps({'status': 'error'})
        except Exception:
            return json.dumps({'status': 'error'})  # Handle other exceptions gracefully



    @http.route('/payment/clik2pay/cancel', type='jsonrpc', auth='public')
    def get_payment_cancel(self, token=None, provider_id=None):
        try:
            # Call the get_payment_status method to check the payment status
            payment_status = self.get_payment_status(token, provider_id)

            if payment_status == 'completed':
                # Payment has already been completed, return completed status
                return json.dumps({'status': 'completed'})
            else:
                # Payment is not completed, attempt cancellation
                provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
                payload = {
                    'payment_request_id': token
                }
                response = provider_sudo._clik2pay_make_request(f'cancel_payment_request', payload=payload, method='POST')
                # _logger.info("devAp: cancel order %s", response)
                if response and 'event' in response and response['event']['status'] == 'CANCELLED':
                    # Payment has been successfully cancelled
                    tx_sudo = request.env['payment.transaction'].sudo().search([('clik2pay_reference', '=', token)])
                    if tx_sudo:
                        tx_sudo._set_canceled(state_message="Payment canceled")
                    return json.dumps({'status': 'cancelled'})
                else:
                    # Handle other cases where the cancellation may not be successful
                    return json.dumps({'status': 'failed'})
        except Exception:
            return json.dumps({'status': 'error'})  # Handle other exceptions gracefully
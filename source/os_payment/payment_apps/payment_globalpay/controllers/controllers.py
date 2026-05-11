# -- coding: utf-8 --

import base64
import binascii
import hashlib
import hmac
import logging
import pprint
import re
from werkzeug import urls
from werkzeug.exceptions import Forbidden

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request, Response

import requests
import json
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


def remove_charandaccents(string):
    if string != None:
        return re.sub(r'[^ \nA-Za-z0-9/]+', '', string)
    else:
        return ''


class GlobalPayWebhookController(http.Controller):
    _webhook_url = '/payment/globalpay/notification'
    _payment_url = '/payment/globalpay/payment'

    @http.route('/payment/globalpay/access_token', type='jsonrpc', auth='public')
    def get_globalpay_access_token(self, permissions=False):
        # Get the current payment provider
        payment_provider = request.env['payment.provider'].sudo().search([('code', '=', 'globalpay')], limit=1)

        # Check if the payment provider is found
        if payment_provider:
            # Call the get_globalpay_access_token method with the provided permissions
            access_token = payment_provider.get_globalpay_access_token(permissions)

            # Return the access token as a JSON response
            return {'access_token': access_token}
        else:
            # Handle the case where the payment provider is not found
            return {'error': 'Payment provider not found'}

    @http.route('/payment/globalpay/store_payment_method', type='jsonrpc', auth='public', csrf=False, methods=['POST'])
    def store_payment_method(self, **params):
        try:
            # Extract parameters from the request
            reference = params.get('reference')
            usage_mode = params.get('usage_mode', 'SINGLE')  # Default to SINGLE if not provided
            card_number = params.get('card_number')
            expiry_month = params.get('expiry_month')
            expiry_year = params.get('expiry_year')
            cvv = params.get('cvv')
            accessToken = params.get('accessToken')

            payload = {
                "account_name": "",
                "reference": f'{card_number}-token-{reference}',
                "usage_mode": usage_mode,
                "card": {
                    "number": card_number,
                    "expiry_month": expiry_month,
                    "expiry_year": expiry_year,
                    "cvv": cvv
                }
            }
            _logger.info("payload %s", payload)
            payment_provider = request.env['payment.provider'].sudo().search([('code', '=', 'globalpay')], limit=1)

            # Make the request to Global Payments (you may need to adjust the endpoint)
            if payment_provider:
                # response = payment_provider._globalpay_make_request('ucp/payment-methods', payload=payload)
                response = payment_provider._globalpay_make_request('payment_tokenization_request', payload=payload)
                _logger.info("devApp: response 1 %s", response)
                # Process the response and return it
                return response

        except Exception as e:
            # Handle exceptions, log the error, and return an appropriate response
            error_message = f"Error processing payment method: {str(e)}"
            return Response(error_message, status=500, content_type='text/plain')

    @http.route(_payment_url, type='jsonrpc', auth='public')
    def make_payment(self, reference, provider_id, currency_id, access_token, partner_id, payment_ref, amount,
                     token_response):
        # Make the payment request to globalpay
        provider_sudo = request.env['payment.provider'].sudo().search([('code', '=', 'globalpay')], limit=1)

        # Check that the transaction details have not been altered. This allows preventing users
        # from validating transactions by paying less than agreed upon.
        # if provider_sudo and provider_sudo.globalpay_tampered_payment:
        #     if not payment_utils.check_access_token(
        #             access_token, reference, converted_amount, partner_id
        #     ):
        #         raise ValidationError("globalpay: " + _("Received tampered payment request data."))

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        currency = request.env['res.currency'].sudo().browse(currency_id)
        partner = request.env['res.partner'].sudo().browse(partner_id)
        partner_name = partner.name.replace(" ", "") if partner else 'public'
        data = {
            "account_name": 'transaction_processing',
            "type": 'SALE',
            "channel": 'CNP',
            "amount": int(float(amount or 0.01) * 10 ** currency.decimal_places),
            "currency": currency.name,
            "reference": f'{partner_name}-token-{reference}'[:50],
            "country": 'US',
            "payment_method": {
                "id": payment_ref,
                "entry_mode": 'ECOM'
            }
        }

        response = None
        try:
            response = provider_sudo._globalpay_make_request('payment_transaction_request', payload=data)

            # Handle the payment request response
            _logger.info("payment request response: %s", pprint.pformat(response))

            # if the merchantOrderId already exists in globalpay and you try to pay again, the createInvoice return
            # So her we check, if he response is string thne
            if isinstance(response, str):
                tx_sudo._set_error(response)
                raise ValidationError(
                    "globalpay: " + _("Create Invoice response %(ref)s.", ref=response)
                )
            tx_sudo.write({
                'provider_reference': response.get('id'),
                'globalpay_reference': response.get('id'),
            })
            tx_sudo._process(
                'globalpay', dict(response, payment_ref=token_response),  # Match the transaction
            )
            return json.dumps(response)
        except requests.exceptions.RequestException:
            _logger.exception("Error wit globalpay service %s", json.dumps(response))
            raise ValidationError(
                "Detail: " + response.get('detail', _("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", str(e))

            raise ValidationError(str(e))
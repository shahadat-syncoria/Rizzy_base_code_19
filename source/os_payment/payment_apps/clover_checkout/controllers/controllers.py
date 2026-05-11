# -*- coding: utf-8 -*-
from odoo import http
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
from odoo.addons.payment.controllers.portal import PaymentPortal

import requests
import json
from odoo.addons.payment import utils as payment_utils

_logger = logging.getLogger(__name__)


class CloverCheckoutController(http.Controller):
    _payment_url = '/payment/clovercheckout/payment'

    @http.route('/payment/clovercheckout/get_provider_info', type='jsonrpc', auth='public')
    def clover_checkout_get_provider_info(self, provider_id):
        """ Return public information on the provider.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        return {
            'state': provider_sudo.state,
            # The public API key solely used to identify the seller account with Authorize.Net
            # 'clover_private_key': provider_sudo.clover_private_key,
            # The public client key solely used to identify requests from the Accept.js suite
            'clover_public_key': provider_sudo.clover_public_api_key,
            # 'clover_merchant_id': provider_sudo.clover_merchant_id
        }

    @http.route('/payment/clovercheckout/store_payment_method', type='jsonrpc', auth='public', csrf=False,
                methods=['POST'])
    def store_payment_method(self, **params):
        try:
            # Extract parameters from the request
            reference = params.get('reference')
            usage_mode = params.get('usage_mode', 'SINGLE')  # Default to SINGLE if not provided
            card_number = params.get('card_number')
            expiry_month = params.get('expiry_month')
            expiry_year = params.get('expiry_year')
            cvv = params.get('cvv')
            accessToken = params.get('token')
            partner = request.env['res.partner'].sudo().browse(params.get('partner_id'))
            # window_location = params.get('window_location')

            payload = {
                "ecomind": "ecom",
                "shipping": {
                    "address": {
                        "city": partner.city,
                        "country": partner.country_id.code,
                        "line1": partner.street,
                        "postal_code": partner.zip,
                        "state": partner.state_id.name
                    }
                },
                "email": partner.email,
                "name": partner.name,
                "source": params.get('token')
            }
            _logger.info("payload %s", payload)
            payment_provider = request.env['payment.provider'].sudo().search([('code', '=', 'clover_checkout')],
                                                                             limit=1)
            # tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', params.get('reference'))])

            # Make the request to Global Payments (you may need to adjust the endpoint)
            if payment_provider:
                # response = payment_provider._globalpay_make_request('ucp/payment-methods', payload=payload)
                response = payment_provider._clover_checkout_make_request("create_customer", payload=payload,
                                                                          )
                _logger.info("devApp: response 1 %s", response)
                # if window_location == '/my/payment_method':
                #     tx_sudo._clover_checkout_tokenize_from_notification_data(response)
                # Process the response and return it
                return response

        except Exception as e:
            # Handle exceptions, log the error, and return an appropriate response
            error_message = f"Error processing payment method: {str(e)}"
            return Response(error_message, status=500, content_type='text/plain')

    @http.route('/payment/clovercheckout/save_payment_token', type='jsonrpc', auth='public')
    def save_payment_token(self, **params):
        try:
            card = params.get('token_id')
            token = request.env['payment.token'].sudo().search([('clover_checkout_id', '=', card)])
            tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', params.get('reference'))])
            if not token :
                token = request.env['payment.token'].create({
                    'provider_id': params.get('provider_id'),
                    'payment_method_id': params.get('payment_method_id'),
                    'payment_details': card[-4:],
                    'partner_id': params.get('partner_id'),
                    'provider_ref': params.get('token_id'),
                    'clover_checkout_id': params.get('token_id'),
                    'clover_customer_id': params.get('clover_checkout_id')
                    # 'payment_method_id': self.payment_method_id.id,
                    # 'verified': True,  # The payment is authorized, so the payment method is valid
                })
            tx_sudo.write({
                    'provider_reference': params.get('token_id'),
                    'clover_checkout_reference': params.get('token_id'),
                })
            tx_sudo._set_done(state_message="Transaction captured")


        except Exception as e:
            # Handle exceptions, log the error, and return an appropriate response
            error_message = f"Error saving payment method: {str(e)}"
            return Response(error_message, status=500, content_type='text/plain')


    @http.route(_payment_url, type='jsonrpc', auth='public')
    def clover_checkout_make_payment(self, **params):
        # Make the payment request to clover_checkout
        provider_sudo = request.env['payment.provider'].sudo().search([('code', '=', 'clover_checkout')], limit=1)

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', params.get('reference'))])
        currency = request.env['res.currency'].sudo().browse(params.get('currency_id'))
        partner = request.env['res.partner'].sudo().browse(params.get('partner_id'))
        # Keep Odoo 18 behavior: charge with customer id returned by create_customer (response.id).
        # Fallback to legacy fields only when access_token is absent.
        source_id = (
            params.get('access_token')
            or params.get('clover_checkout_id')
            or params.get('source_token')
            or params.get('source')
            or params.get('clover_data_id')
        )
        if not source_id:
            raise ValidationError(_("Missing Clover source id; cannot create charge request."))

        data = {
            "ecomind": "ecom",
            "metadata": {
                "existingDebtIndicator": False
            },

            # "amount": 1,
            "amount": int(float(params.get('amount')) * 10 ** currency.decimal_places),
            "currency": currency.name,
            # "currency": 'USD',
            "source": source_id
        }

        response = None
        try:
            response = provider_sudo._clover_checkout_make_request("charge_payment", payload=data)

            # Handle the payment request response
            _logger.info("payment request response: %s", pprint.pformat(response))

            # if the merchantOrderId already exists in clover_checkout and you try to pay again, the createInvoice return
            # So her we check, if he response is string thne
            if isinstance(response, str):
                tx_sudo._set_error(response)
                raise ValidationError(
                    "clover_checkout: " + _("Create Invoice response %(ref)s.", ref=response)
                )
            tx_sudo.write({
                'provider_reference': response.get('id'),
                'clover_checkout_reference': response.get('ref_num'),
                'clover_data_id': params.get('clover_data_id')
            })
            tx_sudo._process(
                'clover_checkout', dict(response),  # Match the transaction
            )
            return json.dumps(response)
        except requests.exceptions.RequestException:
            _logger.exception("Error with clover_checkout service %s", json.dumps(response))
            raise ValidationError(
                "Detail: " + response.get('detail', _("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", str(e))

            raise ValidationError(str(e))
class CloverCheckoutTokenController(PaymentPortal):


    @http.route('/payment/archive_token', type='jsonrpc', auth='user')
    def archive_token(self, token_id):
        """ Check that a user has write access on a token and archive the token if so.

        :param int token_id: The token to archive, as a `payment.token` id
        :return: None
        """
        token_obj = request.env['payment.token'].sudo().browse(token_id)
        provider_sudo = request.env['payment.provider'].sudo().search([('code', '=', 'clover_checkout')], limit=1)
        try:
            if token_obj.provider_id.code == 'clover_checkout':
                payload={
                    "clover_checkout_id": token_obj.clover_checkout_id,
                    "clover_customer_id": token_obj.clover_customer_id,
                }
                response = provider_sudo._clover_checkout_make_request("delete_customer",  payload=payload)
                # srm = AppPayment(service_name='bambora_checkout', service_type='profile_delete', service_key=token_obj.provider_id.token)
                # srm.data = payload
                # response = srm.payment_process(company_id=token_obj.provider_id.company_id.id)
                #
                # if  response.get('error') != None or 'errors_message'  in response:
                #     error = response.get('error') if 'error' in response else response.get("errors_message")
                #     raise Exception(f"{error}")

                # else:
                if response.get('deleted'):
                    _logger.info("Deleted Information %s", response)
                    pass
                else:
                    raise Exception(f"{response.get('message')}")

        except Exception as e:
            raise ValidationError(f"{e}")

        return super().archive_token(token_id)

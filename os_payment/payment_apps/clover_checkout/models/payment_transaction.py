# -*- coding: utf-8 -*-

import logging

from werkzeug import urls

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare
from odoo.addons.payment import utils as payment_utils
import pprint
import json
from odoo.addons.payment import utils as payment_utils
import requests

# from odoo.odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class CloverPaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    clover_checkout_reference = fields.Char('clover Checkout Reference')
    clover_checkout_merchant_transaction_id = fields.Char('Clover Checkout Merchant Transaction Id')
    clover_checkout_merchant_id = fields.Char('Clover Checkout Merchant Id')
    clover_checkout_refund_status = fields.Char()
    clover_checkout_id = fields.Char()
    clover_data_id = fields.Char()

    @staticmethod
    def _clover_checkout_get_error_message(payload, default_message=None):
        """Extract a readable error message from Clover responses with inconsistent shapes."""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            error = payload.get('error')
            if isinstance(error, dict):
                return error.get('message') or error.get('detail') or default_message
            if isinstance(error, str):
                return error
            return payload.get('message') or payload.get('detail') or default_message
        return default_message



    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'clover_checkout':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }



    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return clover_checkout-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        # print("Processing Values--", processing_values)
        if self.provider_code != 'clover_checkout':
            return res
        return
    
    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on clover_checkout data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super(CloverPaymentTransaction,self)._get_tx_from_notification_data(provider_code,notification_data)
        if provider_code != 'clover_checkout' or len(tx) == 1: # check if issue
            return tx
        reference = notification_data.get('id')
        if not reference:
            raise ValidationError("clover_checkout: " + _("Missing reference %s.", reference))
        tx = self.search([('clover_checkout_reference', '=', reference),
                          ('provider_code', '=', 'clover_checkout')])
        if not tx:
            raise ValidationError("clover_checkout: " + _("Invalid transaction reference %s.", reference))
        return tx

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to bypass strict amount parsing from Clover payload."""
        if self.provider_code != 'clover_checkout':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': self.amount,
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, notification_data):
        """ Override of payment to process the transaction based on clover_checkout data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._apply_updates(notification_data)
        if self.provider_code != 'clover_checkout':
            return

        _logger.info("notification_data %s", notification_data)
        event_code = (notification_data.get('status') or '').lower()
        _logger.info('devAp  event_code %s', event_code)

        if event_code:
            if event_code in ('succeeded', 'captured', 'funded', 'paid'):
                self._set_done(state_message="Transaction captured")
            elif event_code in ('initiated', 'pending', 'preauthorized'):
                self._set_pending(state_message="Transaction pending")
            elif event_code in ('reversed', 'failed', 'declined', 'rejected'):
                self._set_error(state_message="Transaction failed")
            else:
                self._set_error(state_message="Unhandled transaction status")
            if self.tokenize:
                self._clover_checkout_tokenize_from_notification_data(notification_data)
                _logger.info(
                    "Received data with an unhandled transaction status (%s) for transaction with reference %s",
                    event_code, self.reference,
                )
        else:
            self._set_error(state_message=self._clover_checkout_get_error_message(
                notification_data, "Invalid transaction status"
            ))
            _logger.info(
                "received data with invalid transaction status (%s) for transaction with reference %s",
                notification_data.get('status'), self.reference,
            )
            
            
    def _clover_checkout_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        self.ensure_one()

        # card = additional_data.get('card',{}).get('masked_number_last4','')
        card = notification_data.get('source', {}).get('id', '')
        token = self.env['payment.token'].sudo().search([('partner_id','=',self.partner_id.id),('clover_checkout_id','=',card)])
        if not token:
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'payment_method_id': self.payment_method_id.id,
                'payment_details': notification_data.get('source',{}).get('last4',''),
                'partner_id': self.partner_id.id,
                'provider_ref': notification_data.get('ref_num'),
                'clover_checkout_id': notification_data.get('source',{}).get('id',''),
                'clover_customer_id': self.clover_data_id,
                # 'global_shopper_reference': additional_data.get('id'),
                # 'payment_method_id': self.payment_method_id.id,
                # 'verified': True,  # The payment is authorized, so the payment method is valid
            })
        self.write({
            'token_id': token,
            'tokenize': False,
        })
        _logger.info(
            "created token with id %(token_id)s for partner with id %(partner_id)s from "
            "transaction with reference %(ref)s",
            {
                'token_id': token.id,
                'partner_id': self.partner_id.id,
                'ref': self.reference,
            },
        )
    
    
    def _send_payment_request(self):
        """ Override of payment to send a payment request to Adyen.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        super()._send_payment_request()
        if self.provider_code != 'clover_checkout':
            return


        if not self.token_id:
            raise UserError("clover_checkout: " + _("The transaction is not linked to a token."))

        tx_sudo = self
        currency = self.currency_id

        data = {
            "ecomind": "ecom",
            "metadata": {
                "existingDebtIndicator": False
            },

            "amount":tx_sudo.amount  ,
            "currency": currency.name,
           "source": self.token_id.clover_checkout_id
        }

        response = None
        try:
            response = self.provider_id._clover_checkout_make_request('charge_payment', payload=data)

            # Handle the payment request response
            _logger.info("payment request response: %s", pprint.pformat(response))

            # if the merchantOrderId already exists in clover_checkout and you try to pay again, the createInvoice return
            # So her we check, if he response is string thne
            if not isinstance(response, dict):
                error_message = self._clover_checkout_get_error_message(
                    response, _("Unexpected Clover response.")
                )
                tx_sudo._set_error(error_message)
                raise ValidationError(
                    "clover_checkout: " + _("Create Invoice response %(ref)s.", ref=error_message)
                )
            if response.get('error'):
                error_message = self._clover_checkout_get_error_message(
                    response, _("Payment request was rejected by Clover.")
                )
                tx_sudo._set_error(error_message)
                raise ValidationError(error_message)
            tx_sudo.write({
                'provider_reference': response.get('id'),
                'clover_checkout_reference': response.get('id'),
                'tokenize': False,
            })
            # self.write({
            #     'token_id': token,
            #     'tokenize': False,
            # })
            tx_sudo._process(
                'clover_checkout', dict(response, payment_ref=self.token_id),  # Match the transaction
            )
            return json.dumps(response)
        except requests.exceptions.RequestException:
            _logger.exception("Error with clover_checkout service %s", json.dumps(response))
            raise ValidationError(
                "Detail: " + self._clover_checkout_get_error_message(
                    response, _("Could not establish the connection to the API.")
                ))
        except Exception as e:
            _logger.error("error during the payment: %s", str(e))

            raise ValidationError(str(e))

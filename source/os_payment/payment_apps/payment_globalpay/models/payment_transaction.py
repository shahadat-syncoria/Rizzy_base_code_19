# -*- coding: utf-8 -*-
# © Syncoria Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Module: payment_globalpay
# This module contains functionality for interacting with the GlobalPay API,


import logging

from werkzeug import urls

from odoo import  api, models, fields
from odoo.exceptions import ValidationError, UserError
from odoo.tools.float_utils import float_compare
from odoo.addons.payment import utils as payment_utils
import pprint
import json
from odoo.addons.payment import utils as payment_utils
import requests

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    globalpay_reference = fields.Char('globalpay Reference')
    globalpay_merchant_transaction_id = fields.Char('globalpay Merchant Transaction Id')
    globalpay_merchant_id = fields.Char('globalpay Merchant Id')
    click2pay_refund_status = fields.Char()
    demo_success_failed = fields.Selection([('CAPTURED', 'Success'), ('DECLINED', 'Failed')])

    # groups = "base.group_no_one"

    # === BUSINESS METHODS ===#
    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return globalpay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'globalpay':
            return res
        currency = self.env['res.currency'].browse(self.currency_id.id).exists()
        to_currency = self.env['res.currency'].search([('name', '=', 'CAD')])
        company = self.env['res.company'].browse(self.company_id.id).exists()
        date = fields.Date.context_today(self)

        if company.currency_id.name != 'CAD':
            _logger.info('not cad %s', currency._convert(self.amount, to_currency, company, date))
            converted_amount = currency._convert(self.amount, to_currency, company, date)
        else:
            _logger.info('yes cad %s', self.amount)
            converted_amount = self.amount

        return {
            'converted_amount': converted_amount,
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'],
                converted_amount,
                processing_values['partner_id']
            )
        }

    def _get_specific_rendering_values(self, processing_values):
        """ Override of payment to return globalpay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        # print("Processing Values--", processing_values)
        if self.provider_code != 'globalpay':
            return res
        return

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on globalpay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'globalpay' or len(tx) == 1:
            return tx
        reference = notification_data['resource'].get('id')
        if not reference:
            raise ValidationError("globalpay: " + ("Missing reference %s.", reference))
        tx = self.search([('globalpay_reference', '=', reference),
                          ('provider_code', '=', 'globalpay')])
        if not tx:
            raise ValidationError("globalpay: " + ("Invalid transaction reference %s.", reference))
        return tx

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'globalpay':
            return super()._extract_amount_data(payment_data)


        return {
            'amount': self.amount,
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, notification_data):
        """ Override of payment to process the transaction based on globalpay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._apply_updates(notification_data)
        if self.provider_code != 'globalpay':
            return

        _logger.info("notification_data %s", notification_data)
        event_code = notification_data.get('status')
        _logger.info('devAp  event_code %s', event_code)

        if event_code:
            if event_code == 'FOR_REVIEW':
                # Set the transaction state to pending
                self._set_pending(state_message="Transaction is being created and needs review")
            elif event_code == 'INITIATED':
                # Set the transaction state to initiated
                self._set_pending(state_message="Transaction initiated")
            elif event_code == 'PENDING':
                # Set the transaction state to pending
                self._set_pending(state_message="Transaction pending")
            elif event_code == 'PREAUTHORIZED':
                # Set the transaction state to pending
                self._set_pending(state_message="Transaction preauthorized")
            elif event_code == 'CAPTURED':
                # Set the transaction state to pending
                self._set_done(state_message="Transaction captured")
            elif event_code == 'FUNDED':
                # Set the transaction state to done
                # if self.tokenize:
                #     self._globalpay_tokenize_from_notification_data(notification_data)
                self._set_done(state_message="Transaction funded")
            elif event_code == 'REVERSED':
                # Set the transaction state to error
                self._set_error(state_message="Transaction reversed")
            elif event_code in ['DECLINED', 'FAILED', 'REJECTED']:
                # Set the transaction state to canceled
                self._set_canceled(state_message="Transaction canceled")
            else:
                # Handle other status codes if needed
                self._set_error(state_message="Unhandled transaction status")
            if self.tokenize:
                self._globalpay_tokenize_from_notification_data(notification_data)
                _logger.info(
                    "Received data with an unhandled transaction status (%s) for transaction with reference %s",
                    event_code, self.reference,
                )
        else:
            self._set_error(state_message="Unhandled transaction status")
            _logger.info(
                "received data with invalid transaction status (%s) for transaction with reference %s",
                notification_data.get('status'), self.reference,
            )

    def _get_post_processing_values(self):
        data = super()._get_post_processing_values()
        if self.provider_code != 'globalpay':
            return data
        return data

    def _handel_refund_status(self, status):
        if status in ['INITIATED', 'PREAUTHORIZED']:
            self._set_pending(state_message="Payment created but pending")
        elif status == 'REVERSED':
            self._set_canceled(state_message="Payment canceled")
        elif status in ['FUNDED','CAPTURED']:
            self._set_done(state_message="Payment settled")
        elif status == 'DECLINED':
            self._set_canceled(state_message="Payment canceled")
        elif status == 'REJECTED':
            self._set_canceled(state_message="Payment canceled")
        else:
            self._set_error(state_message=f"Payment {status.lower()}")
        return

    def _send_refund_request(self):
        """ Override of payment to send a refund request to globalpay.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        if self.provider_code != 'globalpay':
            return super()._send_refund_request()
        refund_tx = self
        refund_data = None

        last_payment_request_id = refund_tx.globalpay_reference

        url = f"/ucp/transactions/{last_payment_request_id}/refund"
        converted_amount = -refund_tx.amount

        payload = {
            "payment_request_id": last_payment_request_id,
            "amount": abs(int(float(converted_amount) * 10 ** self.currency_id.decimal_places))
        }
        try:
            response_content = refund_tx.provider_id._globalpay_make_request('refund_payment_request', payload=payload)
            _logger.info(
                "refund request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(response_content)
            )
            if response_content:
                refund_data = super()._send_refund_request()
                refund_data.globalpay_reference = response_content.get('id')
                refund_data._handel_refund_status(response_content.get('status', 'FAILED'))
            else:
                _logger.exception("Error wit globalpay service %s", json.dumps(response_content))

        except requests.exceptions.RequestException as e:
            _logger.exception("Error wit globalpay service %s", e)
            raise ValidationError(
                "Detail: " + response_content.get('detail', ("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", e)
            raise ValidationError("Globalpay: "+str(e))

        return refund_data

    def _send_void_request(self):
        """ Override of payment to send a void request to globalpay.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'globalpay':
            return

        data = {
            "transaction_request_id": self.provider_reference or self.globalpay_reference
        }

        response_content = self.provider_id._globalpay_make_request(
            endpoint="cancel_payment_request",
            payload=data,
        )
        _logger.info("void request response:\n%s", pprint.pformat(response_content))

        # Handle the void request response
        status = response_content.get('status')
        if status == 'received':
            self._log_message_on_linked_documents((
                "A request was sent to void the transaction with reference %s (%s).",
                self.reference, self.provider_id.name
            ))

    def update_payment_refund_status(self):

        # last_payment_request_id = self.globalpay_reference

        for refund in self.child_transaction_ids or self:
            refund_id = refund.globalpay_reference
            url = f"/ucp/transactions/{refund_id}"

            payload = {
                "transaction_request_id":refund_id
            }
            try:
                response_content = refund.provider_id._globalpay_make_request("get_transaction_request_status",payload=payload)
                _logger.info(
                    "refund request response for transaction with reference %s:\n%s",
                    refund.reference, pprint.pformat(response_content)
                )
                if response_content:
                    refund.click2pay_refund_status = response_content.get('status')
                else:
                    _logger.exception("Error wit globalpay service %s", json.dumps(response_content))
                if refund.demo_success_failed and refund.provider_id.state in ['test']:
                    refund._handel_refund_status(refund.demo_success_failed)
                else:
                    refund._handel_refund_status(refund.click2pay_refund_status or 'FAILED')

            except requests.exceptions.RequestException as e:
                _logger.exception("Error wit globalpay service %s", e)
                raise ValidationError(
                    "Detail: " + response_content.get('detail', ("Could not establish the connection to the API.")))
            except Exception as e:
                _logger.error("error during the payment: %s", e)
                raise ValidationError("Globalpay: " + str(e))

        return

    def sync_refund(self):
        transictions = self.env['payment.transaction'].sudo().search(
            [('provider_code', '=', 'globalpay'), ('child_transaction_ids', '!=', False)])
        for tranc in transictions:
            tranc.update_payment_refund_status()

    def _globalpay_tokenize_from_notification_data(self, notification_data):
        """ Create a new token based on the notification data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        """
        self.ensure_one()

        additional_data = notification_data.get('payment_ref')
        card = additional_data.get('card',{}).get('masked_number_last4','')
        token = self.env['payment.token'].sudo().search([('partner_id','=',self.partner_id.id),('payment_details','=',card)])
        if not token:
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'payment_details': additional_data.get('card',{}).get('masked_number_last4'),
                'partner_id': self.partner_id.id,
                'provider_ref': additional_data.get('account_id'),
                'global_shopper_reference': additional_data.get('id'),
                'payment_method_id': self.payment_method_id.id,
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
        if self.provider_code != 'globalpay':
            return

        # Prepare the payment request to Adyen
        if not self.token_id:
            raise UserError("globalpay: " + ("The transaction is not linked to a token."))

        tx_sudo = self
        currency = self.currency_id.name

        data = {
            "account_name": 'transaction_processing',
            "type": 'SALE',
            "channel": 'CNP',
            "amount": int(float(self.amount) * 10 ** self.currency_id.decimal_places),
            "currency": currency,
            "reference": f'{self.token_id.payment_details}-token-{self.reference}',
            "country": self.env.company.country_id.code,
            "payment_method": {
                "id": self.token_id.global_shopper_reference,
                "entry_mode": 'ECOM'
            }
        }

        response = None
        try:
            response = self.provider_id._globalpay_make_request('payment_transaction_request', payload=data)

            # Handle the payment request response
            _logger.info("payment request response: %s", pprint.pformat(response))

            # if the merchantOrderId already exists in globalpay and you try to pay again, the createInvoice return
            # So her we check, if he response is string thne
            if isinstance(response, str):
                tx_sudo._set_error(response)
                raise ValidationError(
                    "globalpay: " + "Create Invoice response %(ref)s.", ref=response
                )
            tx_sudo.write({
                'provider_reference': response.get('id'),
                'globalpay_reference': response.get('id'),
                'tokenize': False,
            })
            # self.write({
            #     'token_id': token,
            #     'tokenize': False,
            # })
            tx_sudo._process(
                'globalpay', dict(response, payment_ref=self.token_id)  # Match the transaction
            )
            return json.dumps(response)
        except requests.exceptions.RequestException:
            _logger.exception("Error wit globalpay service %s", json.dumps(response))
            raise ValidationError(
                "Detail: " + response.get('detail', ("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", str(e))

            raise ValidationError(str(e))

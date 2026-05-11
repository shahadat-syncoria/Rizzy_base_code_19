# -*- coding: utf-8 -*-

import logging

from werkzeug import urls

from odoo import  api, models, fields
from odoo.exceptions import ValidationError
from odoo.tools.float_utils import float_compare
from odoo.addons.payment import utils as payment_utils
import pprint
import json
from odoo.addons.payment import utils as payment_utils
import requests

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    clik2pay_reference = fields.Char('Clik2Pay Reference')
    clik2pay_merchant_transaction_id = fields.Char('Clik2Pay Merchant Transaction Id')
    clik2pay_merchant_id = fields.Char('Clik2Pay Merchant Id')
    click2pay_refund_status = fields.Char()
    demo_success_failed = fields.Selection([('PAID', 'Success'), ('CANCELLED', 'Failed')])

    # groups = "base.group_no_one"

    # === BUSINESS METHODS ===#
    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return clik2pay-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'clik2pay':
            return res
        currency = self.env['res.currency'].browse(self.currency_id.id).exists()
        to_currency = self.env['res.currency'].search([('name', '=', 'CAD')])
        company = self.env['res.company'].browse(self.company_id.id).exists()
        date = fields.Date.context_today(self)
        
        if company.currency_id.name != 'CAD':
            _logger.info('not cad %s', currency._convert(self.amount, to_currency, company, date))
            converted_amount = currency._convert(self.amount, to_currency, company, date)
        else:
            _logger.info('yes cad %s', self.amount )
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
        """ Override of payment to return clik2pay-specific rendering values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic and specific processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_rendering_values(processing_values)
        # print("Processing Values--", processing_values)
        if self.provider_code != 'clik2pay':
            return res


        # clik2pay_tx_values = dict()

        # payload = {
        #     "type": "ECOMM",
        #     "payer": {
        #         "name": "depositSubmit",
        #         "merchantAccountId": "A0007",
        #         "email": "mdapplemahmud3@gmail.com",
        #         "mobileNumber": "4165551234",
        #         "preferredLanguage": "en"
        #     },
        #     "flexDetails": {
        #         "requested": float(processing_values['amount']),
        #         "minimum": float(processing_values['amount']),
        #         "maximum": float(processing_values['amount'] + 10)
        #     },
        #     "amount": float(processing_values['amount']),
        #     "invoiceNumber": processing_values['reference']
        # }

        # _logger.info("sending '/payment-requests/' request for link creation:\n%s", pprint.pformat(payload))
        # payment_data = self.provider_id._clik2pay_make_request('payment-requests',payload=json.dumps(payload))
        # _logger.info('devApp: payment_data: %s', payment_data)

        # # if the merchantOrderId already exists in clik2pay and you try to pay again, the createInvoice return
        # # So her we check, if he response is string thne
        # if isinstance(payment_data, str):
        #     self._set_error(payment_data)
        #     raise ValidationError(
        #         "clik2pay: " + _("Create Invoice response %(ref)s.", ref=payment_data)
        #     )

        # self.provider_reference = payment_data.get('invoiceNumber')
        # self.clik2pay_reference = payment_data.get('id')
        # self.clik2pay_merchant_transaction_id = payment_data.get('merchantTransactionId')
        # self.clik2pay_merchant_id = payment_data['merchant'].get('id')

        # clik2pay_tx_values.update({
        #     'api_url': payment_data.get('paymentLink'),
        #     'reference': payment_data['invoiceNumber'],
        #     'payment_data': payment_data
        # })
        # return clik2pay_tx_values

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on Clik2Pay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if inconsistent data were received
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'clik2pay' or len(tx) == 1:
            return tx
        reference = notification_data['resource'].get('id')
        if not reference:
            raise ValidationError("clik2pay: " + ("Missing reference %s.", reference))
        tx = self.search([('clik2pay_reference', '=', reference),
                          ('provider_code', '=', 'clik2pay')])
        if not tx:
            raise ValidationError("clik2pay: " + ("Invalid transaction reference %s.", reference))
        return tx

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'clik2pay':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': self.amount,
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, notification_data):
        """ Override of payment to process the transaction based on Clik2Pay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._apply_updates(notification_data)
        if self.provider_code != 'clik2pay':
            return

        event_code = notification_data['resource'].get('status')
        _logger.info('devAp  event_code %s', event_code)

        if event_code:
            if event_code == 'CREATED':
                # Set the transaction state to pending
                self._set_pending(state_message="Payment created but pending")
            elif event_code == 'SCHEDULED':
                # Set the transaction state to pending
                self._set_pending(state_message="Payment scheduled but pending")
            elif event_code == 'PAID':
                # Set the transaction state to done
                self._set_done(state_message="Payment completed")
            elif event_code == 'SETTLED':
                # Set the transaction state to done
                self._set_done(state_message="Payment settled")
            elif event_code == 'FAILED':
                # Set the transaction state to error
                self._set_error(state_message="Payment failed")
            elif event_code == 'CANCELLED':
                # Set the transaction state to canceled
                self._set_canceled(state_message="Payment canceled")
            else:
                # Handle other status codes if needed
                self._set_error(state_message="Payment created but pending")
                _logger.info(
                    "Received data with an unhandled payment status (%s) for transaction with reference %s",
                    event_code, self.reference,
                )
        else:
            _logger.info(
                "received data with invalid payment status (%s) for transaction with reference %s",
                notification_data['resource'].get('status'), self.reference,
            )

    def _get_post_processing_values(self):
        data = super()._get_post_processing_values()
        if self.provider_code != 'clik2pay':
            return data
        return data

    def _handel_refund_status(self, status):
        if status in ['CREATED', 'READY', 'ACTIVE']:
            self._set_pending(state_message="Payment created but pending")
        elif status == 'PAID':
            self._set_done(state_message="Payment completed")
        elif status == 'SETTLED':
            self._set_done(state_message="Payment settled")
        elif status == 'CANCELLED':
            self._set_canceled(state_message="Payment canceled")
        else:
            self._set_error(state_message=f"Payment {status.lower()}")
        return

    def _send_refund_request(self):
        """ Override of payment to send a refund request to Clik2pay.

        Note: self.ensure_one()

        :param float amount_to_refund: The amount to refund
        :return: The refund transaction created to process the refund request.
        :rtype: recordset of `payment.transaction`
        """
        refund_tx = super()._send_refund_request()
        if self.provider_code != 'clik2pay':
            return refund_tx

        last_payment_request_id = refund_tx.source_transaction_id.clik2pay_reference

        url = f"/open/v1/payment-requests/{last_payment_request_id}/refunds"
        converted_amount = payment_utils.to_minor_currency_units(
            -refund_tx.amount,  # The amount is negative for refund transactions
            refund_tx.currency_id,
            arbitrary_decimal_number=2
        )

        payer_email = refund_tx.source_transaction_id.partner_email
        # payer_email = 'mdapplemahmud3@gmail.com'
        payer_mobile = refund_tx.source_transaction_id.partner_phone.replace(' ', '').replace('-', '').replace('+1','') if refund_tx.source_transaction_id.partner_phone else ''

        # payer_mobile = '2505550199'
        converted_amount = -refund_tx.amount

        if self.demo_success_failed:
            payer_mobile = '2505550199'
            converted_amount = -refund_tx.amount

        payload = json.dumps({
            "recipient": {
                "email": f"{payer_email}",
                "mobileNumber": f"{payer_mobile}"
            },
            "amount": converted_amount
        })
        try:
            response_content = refund_tx.provider_id._clik2pay_make_request('refund_payment_request', payload=payload)
            _logger.info(
                "refund request response for transaction with reference %s:\n%s",
                self.reference, pprint.pformat(response_content)
            )
            if response_content:
                refund_tx.click2pay_refund_status = response_content.get('status')
                refund_tx.clik2pay_reference = response_content.get('id')
                refund_tx._handel_refund_status(response_content.get('status', 'FAILED'))
            else:
                _logger.exception("Error wit Clik2Pay service %s", json.dumps(response_content))

        except requests.exceptions.RequestException as e:
            _logger.exception("Error wit Clik2Pay service %s", e)
            raise ValidationError(
                "Detail: " + response_content.get('detail', ("Could not establish the connection to the API.")))
        except Exception as e:
            _logger.error("error during the payment: %s", e)
        return refund_tx

    def update_payment_refund_status(self):

        last_payment_request_id = self.clik2pay_reference

        for refund in self.child_transaction_ids:
            refund_id = refund.clik2pay_reference


            payload = {
                "payment_request_id":last_payment_request_id,
                "refund_request_id":refund_id,
            }
            try:
                response_content = refund.provider_id._clik2pay_make_request('refund_payment_request_status', payload=payload,method='GET')
                _logger.info(
                    "refund request response for transaction with reference %s:\n%s",
                    refund.reference, pprint.pformat(response_content)
                )
                if response_content:
                    refund.click2pay_refund_status = response_content.get('status')
                else:
                    _logger.exception("Error wit Clik2Pay service %s", json.dumps(response_content))
                if refund.demo_success_failed:
                    refund._handel_refund_status(refund.demo_success_failed)
                else:
                    refund._handel_refund_status(refund.click2pay_refund_status or 'FAILED')

            except requests.exceptions.RequestException as e:
                _logger.exception("Error wit Clik2Pay service %s", e)
                raise ValidationError(
                    "Detail: " + response_content.get('detail', ("Could not establish the connection to the API.")))
            except Exception as e:
                _logger.error("error during the payment: %s", e)

        return

    def sync_refund(self):
        transictions = self.env['payment.transaction'].sudo().search(
            [('provider_code', '=', 'clik2pay'), ('child_transaction_ids', '!=', False)])
        for tranc in transictions:
            tranc.update_payment_refund_status()

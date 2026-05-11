# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import pprint

from odoo import api, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.addons.odoosync_base.utils.helper import convert_curency

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'monerischeckout':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }

    def _monerischeckout_create_transaction_request(self, opaque_data):
        """ Create an Moneris Checkout payment transaction request.

        Note: self.ensure_one()

        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return:
        """
        self.ensure_one()

        # authorize_API = AuthorizeAPI(self.provider_id)
        # if self.provider_id.capture_manually or self.operation == 'validation':
        #     return authorize_API.authorize(self, opaque_data=opaque_data)
        # else:
        #     return authorize_API.auth_and_capture(self, opaque_data=opaque_data)
        return {}

    # def _send_payment_request(self):
    #     """ Override of payment to send a payment request to Authorize.
    #
    #     Note: self.ensure_one()
    #
    #     :return: None
    #     :raise: UserError if the transaction is not linked to a token
    #     """
    #     _logger.info("_send_payment_request")
    #     super()._send_payment_request()
    #     if self.provider != 'monerischeckout':
    #         return
    #
    #     if not self.token_id.moneris_profile:
    #         raise UserError("Moneris Checkout: " + ("The transaction is not linked to a token."))
    #
    #     #================================================================================================
    #     # authorize_API = AuthorizeAPI(self.provider_id)
    #     # if self.provider_id.capture_manually:
    #     #     res_content = authorize_API.authorize(self, token=self.token_id)
    #     #     _logger.info("authorize request response:\n%s", pprint.pformat(res_content))
    #     # else:
    #     #     res_content = authorize_API.auth_and_capture(self, token=self.token_id)
    #     #     _logger.info("auth_and_capture request response:\n%s", pprint.pformat(res_content))
    #     # As the API has no redirection flow, we always know the reference of the transaction.
    #     # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
    #     # data in order to go through the centralized `_handle_feedback_data` method.
    #     #================================================================================================
    #     account_invoice_id = self.payment_id.move_id
    #     trnx_amt = self.amount
    #     href = ""
    #     paid_amt = 0
    #     if request.session.sale_order_id:
    #         print("Create Sale Purchase")
    #     else:
    #         res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
    #     feedback_data = {'reference': self.reference, 'response': res_content}
    #     self._handle_feedback_data('monerischeckout', feedback_data)
    
    def _send_payment_request(self):
        """ Override of payment to send a payment request to Moneris Checkout.
    
        Note: self.ensure_one()
    
        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        _logger.info("_send_payment_request")
        super()._send_payment_request()
        if self.provider_code != 'monerischeckout':
            return

        if not self.token_id.moneris_profile:
            _logger.warning("Moneris Checkout: " + ("The transaction is not linked to a token."))

        account_invoice_id = self.payment_id.move_id
        trnx_amt = float(convert_curency(acq=self.provider_id,amount=self.amount,order_currency=self.currency_id))
        href = request.httprequest.url
        paid_amt = 0
        ########################################################################################################
        if request.params and request.params.get('model') == 'account.payment.register':
            context = request.params.get('kwargs', {}).get('context', {})
            active_model = context.get('active_model')
            active_id = context.get('active_id')
            active_ids = context.get('active_ids')

            if (active_model == 'account.move' and active_id) or (active_model == 'account.move' and active_ids):
                account_invoice_id = self.env['account.move'].sudo().browse(active_ids)
                res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
            elif (active_model == 'account.move.line' and active_id) or (active_model == 'account.move.line' and active_ids):
                account_invoice_id = self.env['account.move'].sudo().search([('line_ids', 'in', context.get('active_ids'))])
                res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)

        ########################################################################################################
        elif request.httprequest.url and '/shop/payment' in request.httprequest.url:
            _logger.info("Create Sale Purchase")
            account_invoice_id = self.sale_order_ids
            res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
        elif request.httprequest.url and 'ir.cron' in request.httprequest.url:
            account_invoice_id = self.invoice_ids
            res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
        else:
            res_content = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.

        feedback_data = {'reference': self.reference, 'response': res_content}
        self._process('monerischeckout', feedback_data)

    # def _send_refund_request(self, amount_to_refund=None, create_refund_transaction=True):
    #     """ Override of payment to send a refund request to Authorize.
    #
    #     Note: self.ensure_one()
    #
    #     :param float amount_to_refund: The amount to refund
    #     :param bool create_refund_transaction: Whether a refund transaction should be created or not
    #     :return: The refund transaction if any
    #     :rtype: recordset of `payment.transaction`
    #     """
    #     _logger.info("_send_refund_request")
    #     if self.provider_code != 'monerischeckout':
    #         return super()._send_refund_request(
    #             amount_to_refund=amount_to_refund,
    #             create_refund_transaction=create_refund_transaction,
    #         )
    #
    #     refund_tx = super()._send_refund_request(
    #         amount_to_refund=amount_to_refund, create_refund_transaction=False
    #     )
    #
    #     authorize_API = AuthorizeAPI(self.provider_id)
    #     rounded_amount = round(self.amount, self.currency_id.decimal_places)
    #     res_content = authorize_API.refund(self.provider_reference, rounded_amount)
    #     _logger.info("refund request response:\n%s", pprint.pformat(res_content))
    #     # As the API has no redirection flow, we always know the reference of the transaction.
    #     # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
    #     # data in order to go through the centralized `_handle_notification_data` method.
    #     feedback_data = {'reference': self.reference, 'response': res_content}
    #     self._handle_notification_data('monerischeckout', feedback_data)
    #
    #     return refund_tx

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        _logger.info("_send_capture_request")
        super()._send_capture_request()
        if self.provider_code != 'monerischeckout':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.capture(self.provider_reference, rounded_amount)
        _logger.info("capture request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_notification_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_notification_data('monerischeckout', feedback_data)

    def _send_void_request(self):
        _logger.info("_send_void_request")
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_void_request()
        if self.provider_code != 'monerischeckout':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        res_content = authorize_API.void(self.provider_reference)
        _logger.info("void request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_notification_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_notification_data('monerischeckout', feedback_data)

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Find the transaction based on the feedback data.

        :param str provider: The provider of the provider that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'monerischeckout':
            return tx

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference), ('code', '=', 'monerischeckout')])
        if not tx:
            raise ValidationError(
                "Moneris Checkout: " + ("No transaction found matching reference %s.", reference)
            )
        return tx


    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'monerischeckout':
            return super()._extract_amount_data(payment_data)

        # tx_details = AuthorizeAPI(self.provider_id).get_transaction_details(
        #     payment_data.get('response', {}).get('x_trans_id')
        # )
        # amount = tx_details.get('transaction', {}).get('authAmount')
        # # Authorize supports only one currency per account.
        # currency = self.provider_id.available_currency_ids  # The currency has not been removed from the provider.
        return {
            'amount': self.amount,
            'currency_code': self.currency_id.name,
        }

    def _apply_updates(self, data):
        """ Override of payment to process the transaction based on Moneris Checkout data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        super()._apply_updates(data)
        if self.provider_code != 'monerischeckout':
            return
        print("data ===>>>", data)
        # #============================================================================================
        # response_content = data or {}

        # self.provider_reference = response_content.get('provider_reference')
        # status_code = response_content.get('moneris_response_code')
        # if int(status_code) < 50:  # Approved
        #     status_type = response_content.get('state').lower()
        #     if status_type in ('done'):
        #         self._set_done()
        #         if self.tokenize and not self.token_id:
        #             self._monerischeckout_tokenize()
        #     elif status_type == 'auth_only':
        #         self._set_authorized()
        #         if self.tokenize and not self.token_id:
        #             self._authorize_tokenize()
        #         if self.operation == 'validation':
        #             # Void the transaction. In last step because it calls _handle_notification_data()
        #             self._send_refund_request(create_refund_transaction=False)
        #     elif status_type == 'void':
        #         if self.operation == 'validation':  # Validation txs are authorized and then voided
        #             self._set_done()  # If the refund went through, the validation tx is confirmed
        #         else:
        #             self._set_canceled()
        # elif int(status_code) > 50:   # Declined
        #     self._set_canceled()
        # else:  # Error / Unknown code
        #     error_code = response_content.get('state')
        #     _logger.info(
        #         "received data with invalid status code %s and error code %s",
        #         status_code, error_code
        #     )
        #     self._set_error(
        #         "Moneris Checkout: " + (
        #             "Received data with status code \"%(status)s\" and error code \"%(error)s\"",
        #             status=status_code, error=error_code
        #         )
        #     )
        # #============================================================================================

    def _monerischeckout_tokenize(self):
        """ Create a token for the current transaction.

        Note: self.ensure_one()

        :return: None
        """
        self.ensure_one()

        authorize_API = AuthorizeAPI(self.provider_id)
        cust_profile = authorize_API.create_customer_profile(
            self.partner_id, self.provider_reference
        )
        _logger.info("create_customer_profile request response:\n%s", pprint.pformat(cust_profile))
        if cust_profile:
            token = self.env['payment.token'].create({
                'provider_id': self.provider_id.id,
                'name': cust_profile.get('name'),
                'partner_id': self.partner_id.id,
                'provider_ref': cust_profile.get('payment_profile_id'),
                'authorize_profile': cust_profile.get('profile_id'),
                'authorize_payment_method_type': self.provider_id.authorize_payment_method_type,
                'verified': True,
            })
            self.write({
                'token_id': token.id,
                'tokenize': False,
            })
            _logger.info(
                "created token with id %s for partner with id %s", token.id, self.partner_id.id
            )


    ###########################################################################################
    ###########################################################################################
    def _send_email_tx_failure(self, receipt):
        """[summary]

        Args:
            receipt ([type]): [description]

        Raises:
            UserError: [description]

        Returns:
            [type]: [description]
        """
        self.ensure_one()
        template = self.env.ref('payment_moneris_checkout.email_template_tx_failure')
        print("template ====>>>>", template)
        if not template:
            raise UserError(
                ('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.user_id.sudo().lang
        partner = self.partner_id
        print("lang ====>>>>", lang)
        print("partner ====>>>>", partner)

        # portal_url = partner.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[partner.id]
        partner.signup_prepare()
        # print("portal_url ====>>>>", portal_url)

        template.send_mail(self.id, force_send=True)
        print("template ====>>>>", template)
        return True
        
    ###########################################################################################
    ###########################################################################################
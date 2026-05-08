# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import pprint

from odoo import  api, models, fields
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.addons.odoosync_base.utils.app_payment import AppPayment
from odoo.addons.payment import utils as payment_utils
from .utils import *
_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    bamborachk_auth_code = fields.Char('Auth Code')
    bamborachk_created = fields.Char('Bambora Created on')
    bamborachk_order_number = fields.Char('Order Number')
    bamborachk_txn_type = fields.Char("Transaction Type")
    bamborachk_payment_method = fields.Char("Payment Method")
    bamborachk_card_type = fields.Char("Card Type")
    bamborachk_last_four = fields.Char("Last Four")
    bamborachk_avs_result = fields.Char("AVS Result")
    bamborachk_cvd_result = fields.Char("CVD Result")

    def bamborachk_s2s_do_transaction(self, **data):
        self.ensure_one()
        # tran_profile = None
        false_profiles = self.env['payment.token'].sudo().search([('provider_id.code', '=', 'bamborachk'), (
            'active', '=', True), ('bamborachk_token_type', '!=', 'permanent')])  # ,('bamborachk_profile','=',False)
        for profile in false_profiles:
            tran_profile = profile.sudo().write({'active': False})
        profile = data.get('data')

        data, invoice_payment = get_invoice_flag(data)
        _logger.info("\ninvoice_payment--->"+str(invoice_payment))

        acq = request.env['payment.provider'].sudo().search(
            [('id', '=', int(self.sudo().provider_id))])
        AccMove = self.env['account.move'].sudo()
        ResPartner = self.env['res.partner'].sudo()
        href = data.get("window_href") or request.params.get("window_href")
        # partner = ResPartner.search([('id', '=', int(data.get('partner_id')))])



        # ================= For Register Payment ============================
        account_register_payment = False
        if request.params and request.params.get('model') == 'account.payment.register':
            context = request.params.get('kwargs', {}).get('context', {})
            active_model = context.get('active_model')
            active_id = context.get('active_id')
            active_ids = context.get('active_ids')
            # profile = self.payment_token_id

            if (active_model == 'account.move' and active_id) or (active_model == 'account.move' and active_ids):
                account_invoice_id = self.env['account.move'].sudo().browse(active_ids)
                account_register_payment = True
            elif (active_model == 'account.move.line' and active_id) or (active_model == 'account.move.line' and active_ids):
                account_invoice_id = self.env['account.move'].sudo().search([('line_ids', 'in', context.get('active_ids'))])
                account_register_payment = True
        if acq:
            res_json = {}
            res_json['serverdata'] = {}

            if "/my/invoices" in str(href) or data.get("invoice_payment"):
                invoice_id = data.get("invoice_id")
                invoice = data.get("invoice")
                order_number = str(invoice.name) + "/" + str(get_random_string(6))
                if invoice.state == 'draft':
                    order_number = str(invoice.id) + "/" + str(get_random_string(6))

                partner_name = invoice.partner_id.name
                if len(self.invoice_ids) == 0:
                    self.write({'invoice_ids' : invoice.ids})
                # amount_total = self.invoice_ids[0].amount_total or invoice.amount_total
                amount_total = self.amount or self.invoice_ids[0].amount_total or invoice.amount_total
                res_json['serverdata']['invoice'] = invoice
                res_json['serverdata']['invoice_id'] = invoice_id
            else:
                if account_register_payment:
                    invoice_id = account_invoice_id.id
                    invoice = account_invoice_id
                    order_number = str(invoice.name) + "/" + str(get_random_string(6))
                    if invoice.state == 'draft':
                        order_number = str(invoice.id) + "/" + str(get_random_string(6))

                    partner_name = invoice.partner_id.name
                    if len(self.invoice_ids) == 0:
                        self.write({'invoice_ids': invoice.ids})
                    amount_total = self.invoice_ids[0].amount_total or invoice.amount_total
                    res_json['serverdata']['invoice'] = invoice
                    res_json['serverdata']['invoice_id'] = invoice_id
                else:
                    order_number = self.sale_order_ids[0].name + \
                        "/" + str(get_random_string(6))
                    amount_total = self.sale_order_ids[0].amount_total
                    partner_name = self.sale_order_ids[0].partner_id.name
                    res_json['serverdata']['order'] = self.sale_order_ids[0]
                    res_json['serverdata']['order_id'] = self.sale_order_ids[0].id

            url = 'https://api.na.bambora.com/v1/payments'
            if self.token_id:
                if self.token_id.bamborachk_token_type == 'permanent':
                    profile = self.token_id


            if profile.bamborachk_token_type == 'permanent':
                _logger.info("\n--->permanent")
                req = {
                    "payment_method": "payment_profile",
                    "order_number": order_number,
                    "amount": amount_total,
                    "payment_profile": {
                        "customer_code": profile.bamborachk_profile,
                        "card_id": "1",
                        "complete": "true"
                    }
                }
            else:
                _logger.info("\n--->Temporary")
                req = {
                    "payment_method": "token",
                    "order_number": order_number,
                    "amount": amount_total,
                    "token": {
                        "code": profile.bamborachk_token,
                        "name": partner_name,
                        "complete": "true"
                    }
                }
            _logger.info("\n--->req--->\n"+str(req))

            srm = AppPayment(service_name='bambora_checkout', service_type='payment', service_key=acq.token)
            srm.data = req
            response = srm.payment_process(company_id=acq.company_id.id)
            # response = requests.post(
            #     url, data=json.dumps(req), headers=headers)
            # _logger.info(response.status_code)
            # _logger.info(response.text)
            # if response.status_code == 200:
            if  response == None or 'errors_message' not in response:
                res_json = response
            else:

                _logger.warning(
                                "Payment Response from Bambora:" + str(response))
                profile.write({'active': False})
                _logger.warning("TRANSACTION DECLINED")
                error = 'Payment is not approved %s, Transaction set as error' % (
                    response)
                _logger.warning(error)
                self.sudo()._set_error(
                    error

                )
                self.env.cr.commit()
                return False
        return self._bamborachk_s2s_validate_tree(res_json)

    def _bamborachk_s2s_validate_tree(self, tree):
        return self._bamborachk_s2s_validate(tree)

    def _bamborachk_s2s_validate(self, tree):
        _logger.info(tree)
        tx = self

        # tree['code'] = 1
        # if tree.get('code') == 1:
        if 'approved' in tree:
            if tree.get("approved") == '1':
                if len(self.sale_order_ids) > 0:
                    # self.sale_order_ids[0].write({"state": "sale"})
                    self.sale_order_ids[0].sudo().action_confirm()
                    self.sale_order_ids[0].sudo()._send_order_confirmation_mail()
                _logger.info("TRANSACTION APPROVED")
                transaction = {}
                transaction['provider_reference'] = str(tree.get('authorizing_merchant_id')) + "/" + tree.get(
                    'order_number') if tree.get('authorizing_merchant_id') else tree.get('order_number')
                # transaction['date'] = fields.Datetime.now()
                if len(self.sale_order_ids) > 0:
                    if self.sale_order_ids[0].partner_id:
                        transaction['partner_zip'] = self.sale_order_ids[0].partner_id.zip
                        transaction['partner_city'] = self.sale_order_ids[0].partner_id.city
                        transaction['partner_state_id'] = self.sale_order_ids[0].partner_id.state_id.id
                        transaction['partner_country_id'] = self.sale_order_ids[0].partner_id.country_id.id
                    transaction['partner_country_id'] = self.sale_order_ids[0].partner_id.country_id.id or self.provider_id.company_id.id
                # transaction['state'] = 'done'
                transaction['state_message'] = tree.get('message')
                # transaction['type'] = 'validation'
                transaction['bamborachk_auth_code'] = tree.get('auth_code')
                transaction['bamborachk_created'] = tree.get('created')
                transaction['bamborachk_order_number'] = tree.get('order_number')
                transaction['bamborachk_txn_type'] = tree.get('type')
                transaction['bamborachk_payment_method'] = tree.get('payment_method')
                transaction['bamborachk_card_type'] = tree.get(
                    'card').get('card_type')
                transaction['bamborachk_last_four'] = tree.get(
                    'card').get('last_four')
                transaction['bamborachk_avs_result'] = tree.get(
                    'card').get('avs_result')
                transaction['bamborachk_cvd_result'] = tree.get(
                    'card').get('cvd_result')
                _logger.info(
                    'Validated bambora s2s payment for tx %s: set as done %s' % (tx.reference, transaction))
                tx.write(transaction)
                tx._set_done()
                # tx._reconcile_after_done()
                return True
            else:
                _logger.warning("TRANSACTION DECLINED")
                error = 'Payment is not approved %s, set as error' % (
                    tx.reference)
                _logger.warning(error)
                # tx.write({'state': 'error'})
                tx._set_canceled(
                    error

                )
                # print(self.payment_token)
                return False
        else:
            _logger.warning("TRANSACTION DECLINED")
            error = f'{tree.get("message")}'
            _logger.warning(error)
            # tx.write({'state': 'error'})
            tx._set_error(
                error

            )
            # print(self.payment_token)
            return False

    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        res = super()._get_specific_processing_values(processing_values)
        if self.provider_code != 'bamborachk':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }


    def _send_payment_request(self):
        """ Override of payment to simulate a payment request.

        Note: self.ensure_one()

        :return: None
        """
        super()._send_payment_request()
        if self.provider_code != 'bamborachk':
            return

        if not self.token_id:
            raise UserError("Bambora Checkout: " + ("The transaction is not linked to a token."))

        # simulated_state = self.token_id.demo_simulated_state
        bambora_pay = self.bamborachk_s2s_do_transaction(href=self.landing_route)
        notification_data = {'reference': self.reference, 'simulated_state': bambora_pay}
        self._process('bamborachk', notification_data)

    def _extract_amount_data(self, payment_data):
        """Override of `payment` to extract the amount and currency from the payment data."""
        if self.provider_code != 'bamborachk':
            return super()._extract_amount_data(payment_data)

        return {
            'amount': self.amount,
            'currency_code': self.currency_id.name,
        }



class PaymentToken(models.Model):
    _inherit = 'payment.token'

    bamborachk_profile = fields.Char()
    bamborachk_token = fields.Char()
    bamborachk_token_type = fields.Selection(
        string='Token Type',
        selection=[('temporary', 'Temporary'), ('permanent', 'Permanent')])
    provider = fields.Selection(
        string='Provider', related='provider_id.code', readonly=False)


    def _get_specific_processing_values(self, processing_values):
        """ Override of payment to return an access token as provider-specific processing values.

        Note: self.ensure_one() from `_get_processing_values`

        :param dict processing_values: The generic processing values of the transaction
        :return: The dict of provider-specific processing values
        :rtype: dict
        """
        print("bamborachk--->>>_get_specific_processing_values")
        res = super()._get_specific_processing_values(processing_values)
        if self.code != 'bamborachk':
            return res

        return {
            'access_token': payment_utils.generate_access_token(
                processing_values['reference'], processing_values['partner_id']
            )
        }

    def _bamborachk_create_transaction_request(self, opaque_data):
        """ Create an Moneris Checkout payment transaction request.

        Note: self.ensure_one()

        :param dict opaque_data: The payment details obfuscated by Authorize.Net
        :return:
        """
        print("bamborachk--->>>_bamborachk_create_transaction_request")
        self.ensure_one()

        # authorize_API = AuthorizeAPI(self.provider_id)
        # if self.provider_id.capture_manually or self.operation == 'validation':
        #     return authorize_API.authorize(self, opaque_data=opaque_data)
        # else:
        #     return authorize_API.auth_and_capture(self, opaque_data=opaque_data)
        return {}

    def _send_payment_request(self):
        """ Override of payment to send a payment request to Authorize.

        Note: self.ensure_one()

        :return: None
        :raise: UserError if the transaction is not linked to a token
        """
        print("bamborachk--->>>_send_payment_request")
        super()._send_payment_request()
        if self.code != 'bamborachk':
            return

        if not self.token_id.moneris_profile:
            raise UserError("Bambora Checkout: " + ("The transaction is not linked to a token."))

        #================================================================================================
        # authorize_API = AuthorizeAPI(self.provider_id)
        # if self.provider_id.capture_manually:
        #     res_content = authorize_API.authorize(self, token=self.token_id)
        #     _logger.info("authorize request response:\n%s", pprint.pformat(res_content))
        # else:
        #     res_content = authorize_API.auth_and_capture(self, token=self.token_id)
        #     _logger.info("auth_and_capture request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        #================================================================================================
        account_invoice_id = self.payment_id.move_id
        trnx_amt = self.amount
        href = ""
        paid_amt = 0
        if request.session.sale_order_id:
            print("Create Sale Purchase")
        else:
            res_content = self._bamborachk_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('bamborachk', feedback_data)

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
    #     print("bamborachk--->>>_send_refund_request")
    #     if self.code != 'bamborachk':
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
    #     # data in order to go through the centralized `_handle_feedback_data` method.
    #     feedback_data = {'reference': self.reference, 'response': res_content}
    #     self._handle_feedback_data('bamborachk', feedback_data)
    #
    #     return refund_tx

    def _send_capture_request(self):
        """ Override of payment to send a capture request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        print("bamborachk--->>>_send_capture_request")
        super()._send_capture_request()
        if self.code != 'bamborachk':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        rounded_amount = round(self.amount, self.currency_id.decimal_places)
        res_content = authorize_API.capture(self.provider_reference, rounded_amount)
        _logger.info("capture request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('bamborachk', feedback_data)

    def _send_void_request(self):
        _logger.info("_send_void_request")
        """ Override of payment to send a void request to Authorize.

        Note: self.ensure_one()

        :return: None
        """
        print("bamborachk--->>>_send_void_request")
        super()._send_void_request()
        if self.code != 'bamborachk':
            return

        authorize_API = AuthorizeAPI(self.provider_id)
        res_content = authorize_API.void(self.provider_reference)
        _logger.info("void request response:\n%s", pprint.pformat(res_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': self.reference, 'response': res_content}
        self._handle_feedback_data('bamborachk', feedback_data)

    @api.model
    def _get_tx_from_feedback_data(self, provider, data):
        """ Find the transaction based on the feedback data.

        :param str provider: The provider of the provider that handled the transaction
        :param dict data: The feedback data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        """
        print("bamborachk--->>>_get_tx_from_feedback_data")
        tx = super()._get_tx_from_feedback_data(provider, data)
        if provider != 'bamborachk':
            return tx

        reference = data.get('reference')
        tx = self.search([('reference', '=', reference), ('code', '=', 'bamborachk')])
        if not tx:
            raise ValidationError(
                "Bambora Checkout: " + ("No transaction found matching reference %s.", reference)
            )
        return tx

    def _process_feedback_data(self, data):
        """ Override of payment to process the transaction based on Moneris Checkout data.

        Note: self.ensure_one()

        :param dict data: The feedback data sent by the provider
        :return: None
        """
        print("bamborachk--->>>_process_feedback_data")
        super()._process_feedback_data(data)
        if self.code != 'bamborachk':
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
        #             self._bamborachk_tokenize()
        #     elif status_type == 'auth_only':
        #         self._set_authorized()
        #         if self.tokenize and not self.token_id:
        #             self._authorize_tokenize()
        #         if self.operation == 'validation':
        #             # Void the transaction. In last step because it calls _handle_feedback_data()
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
        #         "Bambora Checkout: " + (
        #             "Received data with status code \"%(status)s\" and error code \"%(error)s\"",
        #             status=status_code, error=error_code
        #         )
        #     )
        # #============================================================================================

    def _bamborachk_tokenize(self):
        """ Create a token for the current transaction.

        Note: self.ensure_one()

        :return: None
        """
        print("bamborachk--->>>_bamborachk_tokenize")
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
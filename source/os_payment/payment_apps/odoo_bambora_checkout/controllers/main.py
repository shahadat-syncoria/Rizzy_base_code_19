# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
from datetime import timedelta
from werkzeug import urls, utils
from odoo import fields,http, tools
from odoo.exceptions import ValidationError, UserError
from odoo.http import request
import random
import string
from datetime import timedelta
from odoo.addons.payment import utils as payment_utils
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

import psycopg2

from odoo import fields, http


_logger = logging.getLogger(__name__)

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str

class bamboraController(http.Controller):
    _notify_url = '/payment/bamborachk/ipn/'
    _return_url = '/payment/bamborachk/return/'
    _cancel_url = '/payment/bamborachk/cancel/'

    @http.route([
        '/payment/bamborachk/return/',
        '/payment/bamborachk/cancel/',
    ], type='http', auth='public', csrf=False)
    def bamborachk_form_feedback(self, **post):
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'bamborachk')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return request.render('payment_bamborachk_checkout.payment_bamborachk_redirect', {
            'return_url': urls.url_join(base_url, "/payment/process")
        })
    

    @http.route('/payment/bamborachk/get_provider_info', type='jsonrpc', auth='public')
    def bamborachk_get_provider_info(self, provider_id):
        """ Return public information on the provider.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        provider_sudo = request.env['payment.provider'].sudo().browse(provider_id).exists()
        return {
            'state': provider_sudo.state,
            'bamborachk_transaction_type': provider_sudo.bamborachk_transaction_type,
            # 'bamborachk_merchant_id': provider_sudo.bamborachk_merchant_id,
            # 'bamborachk_payment_api': provider_sudo.bamborachk_payment_api,
            # 'bamborachk_profile_api': provider_sudo.bamborachk_profile_api,
            'bamborachk_order_confirmation': provider_sudo.bamborachk_order_confirmation,
            'fees_active': provider_sudo.fees_active,
            'fees_dom_fixed': provider_sudo.fees_dom_fixed,
            'fees_dom_var': provider_sudo.fees_dom_var,
            'fees_int_fixed': provider_sudo.fees_int_fixed,
        }

     
    @http.route('/payment/bamborachk/payment',type='jsonrpc', auth="none", methods=['POST'], csrf=False)
    # @http.route('/payment/bamborachk/payment', type='jsonrpc', auth='public')
    def bamborachk_payment(self,  reference,access_token,partner_id,  opaque_data):
        """ Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param dict opaque_data: The payment details obfuscated by bamborachk.Net
        :return: None
        """
        # Check that the transaction details have not been altered
        if not payment_utils.check_access_token(access_token, reference, partner_id):
            raise ValidationError("Moneris Checkout: " + ("Received tampered payment request data."))

        # Make the payment request to bamborachk
        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        tx_sudo._process('bamborachk', opaque_data)
        a = request.session
        request.session['__payment_monitored_tx_id__'] = [tx_sudo.id]
        # self._update_landing_route(tx_sudo, access_token)
        # order_sudo.get_portal_url()
        if "/my/orders/" in opaque_data['window_href']:
            tx_sudo.landing_route = tx_sudo.sale_order_ids.get_portal_url()

        elif "/my/invoices/" in opaque_data['window_href']:
            tx_sudo.landing_route = tx_sudo.invoice_ids.get_portal_url()
        else:
            tx_sudo.landing_route = '/shop/payment/validate'



        # tx_sudo._execute_callback()
        # response_content = tx_sudo._authorize_create_transaction_request(opaque_data)

        # Handle the payment request response
        # _logger.info("make payment response:\n%s",
        #              pprint.pformat(response_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        # feedback_data = {'reference': tx_sudo.reference,
        #                  'response': opaque_data}
        # tx_sudo.sudo()._handle_feedback_data(
        #     'bamborachk', feedback_data
        # )
        # if opaque_data.get('response',{}).get('success') == 'true':
        #     return True
        # else:
        #     return False
        # return True

    # --------------------------------------------------
    # SERVER2SERVER RELATED CONTROLLERS
    # --------------------------------------------------

    @http.route(['/payment/bamborachk/s2s/create_json_3ds'], type='jsonrpc', auth='public', csrf=False)
    def bamborachk_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        order_id = False
        if not order_id:
            if kwargs['window_href'] and 'payment_method' not in kwargs['window_href']:
                if "/my/orders/" in kwargs['window_href']:
                    order_id = kwargs['window_href'].split("/my/orders/")[1].split("?")[0]
                    kwargs['order_id'] = order_id
                    model_name = 'sale.order'
                    sale_order = request.env['sale.order'].browse(int(order_id))
                    if "is_subscription" in sale_order.sudo()._fields:
                        if sale_order.is_subscription:
                            return {
                                'error': "Direct payment of Subscription is not supported . You can pay with saved token ."
                            }

                if "/my/invoices/" in kwargs['window_href']:
                    order_id = kwargs['window_href'].split("/my/invoices/")[1].split("?")[0]
                    kwargs['order_id'] = order_id
                    model_name = 'account.move'
                if '/my/subscription/' in kwargs['window_href']:
                    # order_id = kwargs['window_href'].split("/my/orders/")[1].split("?")[0]
                    # kwargs['order_id'] = order_id
                    # model_name = 'sale.order'
                    return {
                        'error': "Direct payment of Subscription is not supported . You can pay with saved token ."
                    }


            if kwargs['window_href'] and 'payment_method' in kwargs['window_href']:
                if kwargs.get('partner_id'):
                    partner_id = request.env['res.partner'].sudo().search([('id','=',int(kwargs['partner_id']))],order='id desc',limit=1)
                    payment_id = request.env['payment.token'].sudo().search([('partner_id','=',int(kwargs['partner_id']))],order='id desc',limit=1)
                    # kwargs['order_id'] = payment_id.name + "/" + str(payment_id.id) if payment_id else partner_id.name+"/0"
                    # kwargs['order_name'] = payment_id.name + "/" + str(payment_id.id) if payment_id else partner_id.name+"/0"
                    model_name = ''
        if "/shop/payment" in kwargs['window_href'] and 'sale_order_id' in kwargs:
            order_id = request.env['sale.order'].sudo().search([('id','=',int(kwargs.get('sale_order_id')))])
            kwargs['order_name'] = order_id.name
            kwargs['charge_total'] = order_id.amount_total
            model_name = 'sale.order'
            if not order_id.currency_id.active:
                return {
                    'error': "Currency Deactivate"
                }



        token = False
        provider = request.env['payment.provider'].sudo().browse(
            int(kwargs.get('provider_id')))
        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(
                    kwargs, partner_id=request.env.user.partner_id.id)
            token = provider.bamborachk_s2s_form_process(kwargs)

            if '/my/payment_method' in kwargs['window_href']:
                return {
                    'result': False,
                    'partner_id': kwargs.get('partner_id'),
                    "token": payment_id,
                    'verified': False,
                    'window_href': kwargs.get('window_href')
                }
            if not token:
                return {
                    'error': "Token not Created Successfully"
                }

        except ValidationError as e:
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                if request.env.user._is_public():
                    message = ("Please sign in to complete the payment.")
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += (
                            " If you don't have any account, ask your salesperson to grant you a portal access. ")
                else:
                    msg = (
                        "The transaction cannot be processed because some contact details are missing or invalid: ")
                    message = msg + ', '.join(message['missing_fields']) + '. '
                    message += ("Please complete your profile. ")

            return {
                'error': message
            }


        # =================================== Transaction =====================
        # ===============================================================================
        # =========Create a Transaction==================================================
        # ===============================================================================
        # Find the Transaction and Process the transaction

        pay_trnx = request.env['payment.transaction'].sudo()
        target_field = False
        target_id = False

        target_id = order_id
        target_model = model_name
        target_rec = request.env[target_model].sudo().browse(int(target_id))
        target_field = 'sale_order_ids' if model_name == 'sale.order'  else 'invoice_ids'
        reference = pay_trnx._compute_reference(provider, target_rec.name)
        amount_total = target_rec.amount_total
        currency_id = target_rec.currency_id.id

        partner = request.env['res.partner'].sudo().browse(int(kwargs["partner_id"]))
        # last_token_id = request.env['payment.token'].sudo().search([]).id or 0


        print("currency_id ===>>>", currency_id)
        trnx_vals = {
            "provider_id": provider.id,
            "amount": amount_total,
            "currency_id": currency_id,
            "partner_id": int(partner.id),
            "reference": reference,
            "payment_method_id":int(kwargs.get('pay_method')),
            "operation":'online_direct',
            target_field: [int(target_id)] if target_id else False
        }
        if token and token._name == 'payment.token':
            if token.bamborachk_profile:
                trnx_vals.update(
                    {"token_id": token.id}
                )
        tx = pay_trnx.create(trnx_vals)
        print("Transacrtion Created ===>>>>")
        print("tx ===>>>>", tx)
        tx.bamborachk_s2s_do_transaction(data=token)
        # ===============================================================================
        processing_value = {
            'partner_id': kwargs.get('partner_id'),
            'reference': tx.reference,
        }
        get_access_token = tx._get_specific_processing_values(processing_value)

        if not token or tx.state in ['error','cancle']:
            res = {
                'result': False,
                'partner_id': kwargs.get('partner_id'),
                'payment_reference': tx.reference,
                'verified': False,
                'access_token': get_access_token.get('access_token'),
                'window_href': kwargs.get('window_href')
            }
            return res




        res = {
            'result': True,
            'id': token.id,
            'partner_id': kwargs.get('partner_id'),
            'name': token.payment_details,
            'payment_reference':tx.reference,
            '3d_secure': False,
            'verified': True,
            'access_token': get_access_token.get('access_token'),
            'window_href': kwargs.get('window_href')
        }
        _logger.info(res)
        return res

    @http.route(['/payment/bamborachk/s2s/create'], type='http', auth='public')
    def bamborachk_s2s_create(self, **post):
        provider_id = int(post.get('provider_id'))
        provider = request.env['payment.provider'].sudo().browse(provider_id)
        provider.s2s_process(post)
        return utils.redirect("/payment/process")




class BamboraTokenController(PaymentPortal):

# ============================= Token Delete ==============
    @http.route('/payment/archive_token', type='jsonrpc', auth='user')
    def archive_token(self, token_id):
        """ Check that a user has write access on a token and archive the token if so.

        :param int token_id: The token to archive, as a `payment.token` id
        :return: None
        """
        token_obj = request.env['payment.token'].sudo().browse(token_id)
        try:
            if token_obj.provider_id.code == 'bamborachk':
                if token_obj.bamborachk_profile:
                    payload = {
                        "customer_id": token_obj.bamborachk_profile
                    }
                    srm = AppPayment(service_name='bambora_checkout', service_type='profile_delete', service_key=token_obj.provider_id.token)
                    srm.data = payload
                    response = srm.payment_process(company_id=token_obj.provider_id.company_id.id)

                    if  response.get('error') != None or 'errors_message'  in response:
                        error = response.get('error') if 'error' in response else response.get("errors_message")
                        raise Exception(f"{error}")

                    else:
                        if response.get('code') == 1:
                            pass
                        else:
                            raise Exception(f"{response.get('message')}")

        except Exception as e:
            raise ValidationError(f"{e}")

        return super().archive_token(token_id)



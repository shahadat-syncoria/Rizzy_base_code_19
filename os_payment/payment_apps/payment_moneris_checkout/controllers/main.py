# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import pprint
import json
import requests
from werkzeug import urls, utils
from odoo import http, fields, tools, _
from odoo.service import common
from odoo.http import request
from odoo.addons.payment import utils as payment_utils
from odoo.orm.utils import SUPERUSER_ID
from odoo.exceptions import UserError, ValidationError
from odoo.addons.odoosync_base.utils.app_payment import AppPayment
from odoo.addons.odoosync_base.utils.helper import convert_curency

from ..lib import mpgClasses
import random
import string
import re
import pprint
import urllib.parse

_logger = logging.getLogger(__name__)

version_info = common.exp_version()
server_serie = version_info.get('server_serie')


def remove_charandaccents(string):
    if string != None:
        return re.sub(r'[^ \nA-Za-z0-9/]+', '', string)
    else:
        return ''


def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def get_href_params(href):
    href = href.split('?')[1]
    href_params = {}
    for params in href.split('&'):
        href_params[params.split('=')[0]] = params.split('=')[1]
    return href_params


def url_to_dict(url_str):
    url_dict = urllib.parse.parse_qs(url_str)
    print("URL Params : " + str(url_dict))
    return url_dict


def _get_moneris_line_quantity(line):
    quantity = getattr(line, 'product_uom_qty', None)
    if quantity is None:
        quantity = getattr(line, 'quantity', 0.0)
    return float(quantity or 0.0)


def _format_moneris_quantity(quantity):
    if float(quantity).is_integer():
        return str(int(quantity))
    return ('%.4f' % quantity).rstrip('0').rstrip('.')


def _build_moneris_cart(order, acq, invoice_model_name):
    items = []
    untaxed_total = 0.0
    order_model = getattr(order, '_name', '')
    lines = order.invoice_line_ids if order_model == invoice_model_name else order.order_line

    for line in lines:
        if getattr(line, 'display_type', False) or not line.product_id:
            continue

        quantity = _get_moneris_line_quantity(line)
        line_subtotal = float(getattr(line, 'price_subtotal', 0.0) or 0.0)

        if quantity <= 0:
            _logger.info(
                "Skipping Moneris cart preload for %s because line %s has unsupported quantity %s.",
                order.name, line.id, quantity,
            )
            return False

        if line_subtotal < 0:
            _logger.info(
                "Skipping Moneris cart preload for %s because line %s has negative subtotal %s.",
                order.name, line.id, line_subtotal,
            )
            return False

        untaxed_total += line_subtotal
        unit_cost = line_subtotal / quantity
        items.append({
            "url": "",
            "description": remove_charandaccents(line.product_id.name) or '',
            "product_code": str(line.product_id.id) or '',
            "unit_cost": convert_curency(
                acq=acq,
                amount=unit_cost,
                order_currency=order.currency_id if order else acq.company_id.currency_id,
            ) or '',
            "quantity": _format_moneris_quantity(quantity),
        })

    if not items:
        return False

    if abs(untaxed_total - float(order.amount_untaxed or 0.0)) > 0.01:
        _logger.info(
            "Skipping Moneris cart preload for %s because item subtotal %s does not match order untaxed total %s.",
            order.name, untaxed_total, order.amount_untaxed,
        )
        return False

    return {
        "items": items,
        "subtotal": convert_curency(
            acq=acq,
            amount=order.amount_untaxed,
            order_currency=order.currency_id if order else acq.company_id.currency_id,
        ),
        "tax": {
            "amount": convert_curency(
                acq=acq,
                amount=order.amount_tax,
                order_currency=order.currency_id if order else acq.company_id.currency_id,
            ),
            "description": "Taxes",
            "rate": ""
        }
    }


class MonerisController(http.Controller):

    @http.route('/payment/monerischeckout/get_provider_info', type='jsonrpc', auth='public')
    def monerischeckout_get_provider_info(self, provider_id):
        """ Return public information on the provider.

        :param int provider_id: The provider handling the transaction, as a `payment.provider` id
        :return: Information on the provider, namely: the state, payment method type, login ID, and
                 public client key
        :rtype: dict
        """
        print("monerischeckout_get_provider_info")
        provider_sudo = request.env(user=SUPERUSER_ID)['payment.provider'].browse(provider_id).exists()
        print("provider_sudo ===>>>>", provider_sudo)
        return {
            'state': provider_sudo.state,
            'moneris_transaction_type': provider_sudo.moneris_transaction_type,
            # 'moneris_store_id': provider_sudo.moneris_store_id,
            # 'moneris_api_token': provider_sudo.moneris_api_token,
            # 'moneris_checkout_id': provider_sudo.moneris_checkout_id,
            'moneris_store_card': provider_sudo.moneris_store_card,
        }

    @http.route('/payment/monerischeckout/payment', type='jsonrpc', auth="public", methods=['POST'], csrf=False)
    # @http.route('/payment/monerischeckout/payment', type='jsonrpc', auth='public')
    def monerischeckout_payment(self, reference, partner_id, access_token, opaque_data):
        """ Make a payment request and handle the response.

        :param str reference: The reference of the transaction
        :param int partner_id: The partner making the transaction, as a `res.partner` id
        :param str access_token: The access token used to verify the provided values
        :param dict opaque_data: The payment details obfuscated by monerischeckout.Net
        :return: None
        """
        print("--------------------------------------------------------")
        print("reference ===>>>>", reference)
        print("partner_id ===>>>>", partner_id)
        print("access_token ===>>>>", access_token)
        print("opaque_data ===>>>>", opaque_data)
        print("--------------------------------------------------------")
        # Check that the transaction details have not been altered
        # if not payment_utils.check_access_token(access_token, reference, partner_id):
        #     raise ValidationError("Moneris Checkout: " + _("Received tampered payment request data."))

        # Make the payment request to monerischeckout
        tx_sudo = request.env(user=SUPERUSER_ID)['payment.transaction'].search([('reference', '=', reference)])
        moneris_partner_id = opaque_data.get('moneris_partner_id') or opaque_data.get('formData', {}).get('moneris_partner_id')
        if moneris_partner_id and request.env.user.has_group('os_payment.group_moneris_token_manager'):
            partner = request.env(user=SUPERUSER_ID)['res.partner'].browse(int(moneris_partner_id))
            tx_sudo.partner_id = partner
            if opaque_data.get('formData'):
                opaque_data['formData']['partner_id'] = partner.id
        if not tx_sudo.partner_id:
            fallback_partner_id = partner_id or request.env.user.partner_id.id
            tx_sudo.partner_id = request.env(user=SUPERUSER_ID)['res.partner'].browse(int(fallback_partner_id))
            if opaque_data.get('formData'):
                opaque_data['formData']['partner_id'] = int(fallback_partner_id)
        tx_sudo.monerischeckout_s2s_do_transaction(opaque_data)

        # response_content = tx_sudo._authorize_create_transaction_request(opaque_data)

        # Handle the payment request response
        # _logger.info("make payment response:\n%s",
        #              pprint.pformat(response_content))
        # As the API has no redirection flow, we always know the reference of the transaction.
        # Still, we prefer to simulate the matching of the transaction by crafting dummy feedback
        # data in order to go through the centralized `_handle_feedback_data` method.
        feedback_data = {'reference': tx_sudo.reference,
                         'response': opaque_data}
        tx_sudo._process('monerischeckout', feedback_data)
        # request.env['payment.transaction'].sudo()._handle_feedback_data(
        #     'monerischeckout', feedback_data
        # )
        if opaque_data.get('response', {}).get('success') == 'true':
            return True
        else:
            return False

    # --------------------------------------------------
    # SERVER2SERVER RELATED CONTROLLERS
    # --------------------------------------------------

    @http.route(['/payment/monerischeckout/s2s/create_json_3ds'], type='jsonrpc', auth='public', csrf=False)
    def monerischeckout_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        _logger.info("monerischeckout_s2s_create_json_3ds>>>>>>")
        _logger.info("kwargs ********%s", kwargs)

        token = False
        provider = request.env(user=SUPERUSER_ID)['payment.provider'].browse(
            int(kwargs.get('provider_id')))

        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(
                    kwargs, partner_id=request.env.user.partner_id.id)
            token = provider.monerischeckout_s2s_form_process(kwargs)
        except ValidationError as e:
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                if request.env.user._is_public():
                    message = _("Please sign in to complete the payment.")
                    # uimport randompdate message if portal mode = b2b
                    if request.env(user=SUPERUSER_ID)['ir.config_parameter'].get_param('auth_signup.allow_uninvited',
                                                                           'False').lower() == 'false':
                        message += _(
                            " If you don't have any account, ask your salesperson to grant you a portal access. ")
                else:
                    msg = _(
                        "The transaction cannot be processed because some contact details are missing or invalid: ")
                    message = msg + ', '.join(message['missing_fields']) + '. '
                    message += _("Please complete your profile. ")

            return {
                'error': message
            }

        if not token:
            res = {
                'result': False,
            }
            return res

        res = {
            'result': True,
            'id': token.id if token else False,
            'name': token.name if token else False,
            '3d_secure': False,
            'verified': True,
        }
        return res

    @http.route('/payment/monerischeckout/preload', type='jsonrpc', auth="public", methods=['POST'], csrf=False)
    def monerischeckout_preload(self, **post):
        _logger.info("post\n" + str(post))
        order_id = False
        invoice_id = False
        payment_method = False
        target_check = 'account.move'
        href = post.get('href') or request.params.get(
            'href') or request.params.get('window_href')
        if href:
            if '/website_payment' in href or '/payment/pay' in href:
                href_params = get_href_params(href)
                order = href_params.get('order_id')
                domain = [('code', '=', 'sale.order')]
                domain += [('active', '=', True)]
                sale_seq = request.env(user=SUPERUSER_ID)['ir.sequence'].search(
                    domain, limit=1)
                if href_params.get('reference') and sale_seq.prefix in href_params.get('reference'):
                    sale_domain = [('name', '=', href_params.get('reference'))]
                    # sale_domain += [('id', '=', href_params.get('order_id'))]
                    if 'order_id' in href_params:
                        sale_domain += [('id', '=', href_params.get('order_id'))]
                    if 'sale_order_id' in href_params and href_params.get('sale_order_id'):
                        sale_domain += [('id', '=', href_params.get('sale_order_id'))]
                    order_id = request.env(user=SUPERUSER_ID)['sale.order'].search(
                        sale_domain)
                if not order_id or href_params.get('invoice_id'):
                    model = 'account.move'
                    invoice_id = href_params.get('invoice_id')
                    order_id = request.env(user=SUPERUSER_ID)['account.move'].search(
                        [('id', '=', invoice_id)])
            # -----------------------------------
            if '/my/invoices' in href:
                invoice_id = post.get('invoice_id') or href.split(
                    "/my/invoices/")[1].split("?")[0]
                order_id = request.env(user=SUPERUSER_ID)[target_check].search(
                    [('id', '=', int(invoice_id))])
                post.update({
                    'sale_order_id' :""
                })
            if '/my/orders' in href:
                order = post.get('order_id') or href.split(
                    "/my/orders/")[1].split("?")[0]
                order_id = request.env(user=SUPERUSER_ID)['sale.order'].search(
                    [('id', '=', int(order))])

            if '/my/payment_method' in href:
                payment_method = request.env(user=SUPERUSER_ID)['payment.token'].search([], order='id desc', limit=1)
                if payment_method:
                    payment_method = 'payment.token' + \
                                     str(payment_method.id + 1)
                    partner_id = post.get('partner_id')
                    if not partner_id:
                        uid = request.uid
                        user = request.env(user=SUPERUSER_ID)['res.users'].browse(int(uid))
                        partner_id = user.partner_id.id

                    partner = request.env(user=SUPERUSER_ID)['res.partner'].browse(
                        int(partner_id))
                    if partner and partner.country_id.id == False:
                        raise UserError(
                            _("Please setup your Country from `Details` Edit under your username!"))

        if not payment_method:
            if not order_id:
                if post.get('order_id'):
                    order_id = post.get('order_id').replace("/", "")
                    order_id = request.env(user=SUPERUSER_ID)['sale.order'].search(
                        [('id', '=', int(post.get('order_id')))])
            if not invoice_id:
                if post.get('invoice_id'):
                    invoice_id = post.get('invoice_id').replace("/", "")
                    order_id = request.env(user=SUPERUSER_ID)['account.move'].search(
                        [('id', '=', int(invoice_id))])
                elif request.session.get('sale_order_id'):
                    order_id = request.env(user=SUPERUSER_ID)['sale.order'].search(
                        [('id', '=', int(request.session.get('sale_order_id')))])

            if post.get('sale_order_id'):
                order_id = request.env(user=SUPERUSER_ID)['sale.order'].search(
                    [('id', '=', int(post.get('sale_order_id')))])

        data = {}
        provider_id = post.get('provider_id')
        acq = request.env(user=SUPERUSER_ID)['payment.provider'].search(
            [('id', '=', int(provider_id))])

        amount_total = '%.2f' % order_id.amount_total if order_id else '%.2f' % 1.00
        _logger.info("\namount_total\n," + str(amount_total))

        if '/payment/pay' in href and href_params:
            amount_total = '%.2f' % (float(href_params.get('amount')))



        if '/my/payment_method' in href and acq and acq.moneris_transaction_type != 'cardverification':
            error = "Addition of Card is disabled by Moneris Checkout. Please change your Moneris Checkout Settings."
            return json.dumps({'response': {'success': 'false', 'error': error}})
        # if not '/my/payment_method' in href and acq.moneris_transaction_type == 'cardverification':
        #     error = "Popup Checkout disabled.You can pay with saved cards or contact with System Administrator."
        #     return json.dumps({'response': {'success': 'false', 'error': error}})

        if acq:
            # data['store_id'] = acq.moneris_store_id
            # data['api_token'] = acq.moneris_api_token
            # data['checkout_id'] = acq.moneris_checkout_id
            data['txn_total'] = convert_curency(acq=acq, amount=amount_total,order_currency=order_id.currency_id if order_id else acq.company_id.currency_id)

            environment = acq.environment if server_serie == '12.0' else acq.state
            target_check = 'account.invoice' if server_serie == '12.0' else 'account.move'

            if environment == 'test':
                data['environment'] = 'qa'
                # url = 'https://gatewayt.moneris.com/chkt/request/request.php'
            else:
                data['environment'] = 'prod'
                # url = 'https://gateway.moneris.com/chkt/request/request.php'

            data['action'] = "preload"
            order_seq = get_random_string(8)
            if order_id:
                data['order_no'] = order_id.name + '/' + str(order_seq)
                if order_id.partner_id:
                    data['cust_id'] = remove_charandaccents(
                        order_id.partner_id.name) + "/" + str(order_id.partner_id.id)
            else:
                data['order_no'] = str(order_seq)

            # ===============================================================================
            # =========Create a Transaction==================================================
            # ===============================================================================
            # Find the Transaction and Process the transaction

            pay_trnx = request.env(user=SUPERUSER_ID)['payment.transaction']
            target_field = False
            target_id = False

            if acq.moneris_transaction_type != 'cardverification':
                target_id = order_id.id
                target_model = 'sale.order' if 'sale.order' in str(
                    order_id) else 'account.move'
                target_rec = request.env(user=SUPERUSER_ID)[target_model].browse(int(target_id))
                target_field = 'sale_order_ids' if 'sale.order' in str(
                    order_id) else 'invoice_ids'
                reference = pay_trnx._compute_reference(post['provider'], target_rec.name)
                amount_total = target_rec.amount_total
                currency_id = target_rec.currency_id.id

            else:
                if acq.moneris_token != True:
                    response = {
                        "errors_message": "Tokenization disabled ! Please Contact with Administration."
                    }
                    return json.dumps(response)
                    # raise UserError(_("Tokenization disabled ! Please Contact with Administration."))
                amount_total = 0.00
                partner = request.env(user=SUPERUSER_ID)['res.partner'].browse(int(post["partner_id"]))
                # last_token_id = request.env['payment.token'].sudo().search([]).id or 0
                reference = partner.name + '/' + get_random_string(4)

                target_rec = request.env['website'].browse(request.website_routing)
                print("website_id ===>>>", target_rec)
                target_field = 'sale_order_ids'
                currency_id = partner.currency_id.id

            print("currency_id ===>>>", currency_id)
            trnx_vals = {
                "provider_id": int(post['provider_id']),
                "amount": amount_total,
                "currency_id": currency_id,
                "partner_id": int(post["partner_id"]),
                "reference": reference,
                target_field: [int(target_id)] if target_id else False
            }
            # tx = pay_trnx.create(trnx_vals)
            # print("Transacrtion Created ===>>>>")
            # print("tx ===>>>>", tx)
            # ===============================================================================
            data['dynamic_descriptor'] = "dyndesc"
            data['language'] = "en"

            order_seq = get_random_string(8)
            data['order_no'] = reference + ':' + str(order_seq)

            # data['recur'] :{
            #     "bill_now":"true",
            #     "recur_amount":"1.00",
            #     "start_date":"2020-1-1",
            #     "recur_unit":"month",
            #     "recur_period":"1",
            #     "number_of_recurs":"10"
            # },
            if order_id:
                partner_id = order_id.partner_id
                data['contact_details'] = {
                    "first_name": partner_id.name,
                    "last_name": "",
                    "email": partner_id.email if partner_id.email else '',
                    "phone": partner_id.phone if partner_id.phone else ''
                }

                # shipping_details and billing_details removed for errors
                # "error":{"shipping_details":{"postal_code":"Invalid postal code"},
                # "billing_details":{"postal_code":"Invalid postal code"}}}}
                # data['shipping_details'] = {
                #     "address_1":order_id.partner_shipping_id.street or '',
                #     "address_2":order_id.partner_shipping_id.street2 or '',
                #     "city":order_id.partner_shipping_id.city or '',
                #     "province":order_id.partner_shipping_id.state_id.code or '',
                #     "country": order_id.partner_shipping_id.country_id.code or '',
                #     "postal_code": order_id.partner_shipping_id.zip or ''
                # }
                # for key,value in data['shipping_details'].items():
                #     data['shipping_details'][key] = remove_charandaccents(data['shipping_details'][key])
                # if target_check not in str(order_id):
                #     partner_invoice_id = order_id.partner_invoice_id
                # else:
                #     partner_invoice_id = order_id.partner_id
                if acq.moneris_avs:
                    partner_invoice_id = order_id.partner_invoice_id if target_check not in str(
                        order_id) else order_id.partner_id
                    street = partner_invoice_id.street or ''
                    street2 = partner_invoice_id.street2 or ''
                    city = partner_invoice_id.city or ''
                    province = partner_invoice_id.state_id.code or ''
                    country = partner_invoice_id.country_id.code or ''
                    postal_code = partner_invoice_id.zip or ''
                    # data['billing_details'] = {
                    #     "address_1": remove_charandaccents(street) or '',
                    #     "address_2": remove_charandaccents(street2) or '',
                    #     "city": remove_charandaccents(city) or '',
                    #     "province": remove_charandaccents(province) or '',
                    #     "country": remove_charandaccents(country) or '',
                    #     "postal_code": remove_charandaccents(postal_code) or ''
                    # }
                    data['billing_details'] = {
                        "address_1": street or '',
                        "address_2": street2 or '',
                        "city": city or '',
                        "province": province or '',
                        "country": country or '',
                        "postal_code": postal_code or ''
                    }
                try:
                    cart = _build_moneris_cart(order_id, acq, target_check)
                    if cart:
                        data['cart'] = cart
                except Exception:
                    _logger.exception(
                        "Failed to build Moneris cart preload payload for %s.",
                        order_id.name,
                    )

            # response = requests.post(url, data=json.dumps(data))
            srm = AppPayment(service_name='moneris', service_type='preload', service_key=acq.token)
            srm.data = data
            response = srm.payment_process(company_id=acq.company_id.id)

            # _logger.info("Preload Request---->\n" + pprint.pformat(data))
            # _logger.info("Preload Response---->\n" + pprint.pformat(response.text))
            return json.dumps(response)

    @http.route('/payment/monerischeckout/receipt', type='jsonrpc', auth="public", methods=['POST'], csrf=False)
    def monerischeckout_receipt(self, **post):
        _logger.info("monerischeckout_receipt********")
        _logger.info("\npost\n" + pprint.pformat(post))

        pay_trxn = request.env(user=SUPERUSER_ID)['payment.transaction']
        pay_token = request.env(user=SUPERUSER_ID)['payment.token']
        Partner = request.env(user=SUPERUSER_ID)['res.partner']
        payment_acq = request.env(user=SUPERUSER_ID)['payment.provider']

        res = False
        provider_id = post.get('formData').get(
            'provider_id') or post.get('provider_id')
        provider = post.get('provider')
        kwargs = post.get('preload_response')
        kwargs['formData'] = post.get('formData')

        partner_id_value = post.get('formData', {}).get('partner_id')
        if not partner_id_value:
            partner_id_value = request.env.user.partner_id.id
            post.get('formData', {})['partner_id'] = partner_id_value
        partner_id = int(partner_id_value)
        partner = Partner.browse(partner_id)
        currency_id = False
        country_id = partner.country_id if partner else False

        if request.env.uid:
            ResUsers = request.env(user=SUPERUSER_ID)['res.users']
            user_id = ResUsers.search(
                [('id', '=', request.env.uid)])
            currency_id = user_id.company_id.currency_id

        if currency_id == False and '/shop/payment' in post.get('formData', {}).get('window_href'):
            if request.params:
                order_id = request.params.get('formData', {}).get('order_id')
                order = request.env(user=SUPERUSER_ID)['sale.order'].search(
                    [('id', '=', order_id)], limit=1)
                currency_id = order.currency_id

        provider = payment_acq.browse(int(provider_id))
        token = pay_token.search([('moneris_ticket', '=', kwargs.get('ticket'))])

        currency_id = False
        data_request = {}
        environment = provider._get_monerischeckout_environment()
        url = provider._get_monerischeckout_urls(environment).get('moneris_chk_url')
        ticket = kwargs.get('ticket')
        data_request = {
            # "store_id": provider.moneris_store_id,
            # "api_token": provider.moneris_api_token,
            # "checkout_id": provider.moneris_checkout_id,
            "ticket": ticket,
            "environment": environment,
            "action": "receipt"
        }

        
        srm = AppPayment(service_name='moneris', service_type='receipt', service_key=provider.token)
        srm.data = data_request
        response = srm.payment_process(company_id=provider.company_id.id)
        res_json = response

        print("data_request ===>>>", data_request)
        print("res_json ===>>>", str(res_json))

        result = res_json.get('response', {}).get('receipt', {}).get('result')
        if res_json.get('response', {}).get('success') == 'true':
            req = res_json.get('response', {}).get('request', {})
            reference = req.get('order_no').split('/')[0]
            print("reference ===>>>", reference)
            tx = request.env(user=SUPERUSER_ID)['payment.transaction'].search([('reference', '=', req.get('order_no'))])
            res_json['provider_id'] = provider_id
            res_json['formData'] = {}
            res_json['formData'] = kwargs['formData']
            kwargs.get('formData', {}).get('window_href')
            # receipt = tx.monerischeckout_s2s_do_transaction(res_json)

        window_href = post.get('formData').get('window_href')
        window_href = window_href.split("'")[1] if '<Request' in window_href else window_href

        if '/shop/payment' in window_href or '/my/orders' in window_href \
                or '/my/invoices' in window_href or '/pay/invoice' in window_href:
            token.write({'moneris_ticket': kwargs.get('ticket')}) if token else None

        _logger.info("res Response---->\n" + pprint.pformat(res_json))

        if '/pay/invoice' in window_href or '/my/invoice' in window_href or '/payment/pay' in window_href:
            if 'access_token' in window_href:
                url_dict = url_to_dict(window_href)
                print("url_dict ===>>>", url_dict)
                access_token = url_dict.get("access_token")
                print("access_token ===>>>", access_token)
            else:
                access_token = request.env(user=SUPERUSER_ID)['account.move'].browse(int(post['move_id'])).access_token
        elif '/my/payment_method' in window_href:
            access_token = ""
        elif '/my/orders' in window_href:
            if 'access_token' in window_href:
                url_dict = url_to_dict(window_href)
                print("url_dict ===>>>", url_dict)
                access_token = url_dict.get("access_token")
        else:
            access_token = request.env(user=SUPERUSER_ID)['sale.order'].browse(int(res_json['formData']['sale_order_id'])).access_token

        res_json['formData']['access_token'] = access_token
        return res_json

    @http.route(['/payment/monerischeckout/s2s/create'], type='http', auth='public')
    def moneris_checkout_s2s_create(self, **post):
        provider_id = int(post.get('provider_id'))
        provider = request.env(user=SUPERUSER_ID)['payment.provider'].browse(provider_id)
        provider.s2s_process(post)
        return utils.redirect("/payment/process")

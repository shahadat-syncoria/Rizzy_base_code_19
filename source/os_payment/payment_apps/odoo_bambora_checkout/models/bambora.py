# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import base64
import json
from odoo.http import request
from odoo import api, exceptions, fields, models
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.addons.odoosync_base.utils.app_payment import AppPayment
import requests
import logging
import string
import random
import re
import urllib
from urllib.parse import unquote
from odoo.service import common
from .utils import *

version_info = common.exp_version()
server_serie = version_info.get('server_serie')

_logger = logging.getLogger(__name__)



class providerbambora(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('bamborachk', 'Bambora Checkout')],
        ondelete={'bamborachk': 'set default'})
    bamborachk_transaction_type = fields.Selection(
        string=("Transaction Type"),
        selection=[('purchase', ('Purchase'))], default='purchase')
    bamborachk_merchant_id = fields.Char(string='Merchant ID')
    bamborachk_payment_api = fields.Char(string='Payment API')
    bamborachk_profile_api = fields.Char(string='Profile API')
    bamborachk_order_confirmation = fields.Selection(string='Order Confirmation', selection=[
        ('capture', ('Authorize & capture the amount and conform it'))], default='capture')
    fees_active = fields.Boolean(default=False)
    fees_dom_fixed = fields.Float(default=0.35)
    fees_dom_var = fields.Float(default=3.4)
    fees_int_fixed = fields.Float(default=0.35)
    fees_int_var = fields.Float(default=3.9)

    def _get_feature_support(self):
        res = super(providerbambora, self)._get_feature_support()
        res['tokenize'].append('bamborachk')
        return res

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'bamborachk').update({
            'support_tokenization': True,
        })

    def bamborachk_compute_fees(self, amount, currency_id, country_id):
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        return fees

    def bamborachk_url_info(self, url):
        print("bamborachk_url_info")
        move_id = False
        url_dict = url_to_dict(url)
        return url_dict

    @api.model
    def _get_compatible_providers(self, *args, currency_id=None, **kwargs):
        providers = super()._get_compatible_providers(*args, currency_id=currency_id, **kwargs)

        return providers

    # ------------------------------------------------------------------------------------------------
    # ------------------------------------Bambora S2S Actions-----------------------------------------
    # ------------------------------------------------------------------------------------------------

    @api.model
    def bamborachk_s2s_form_process(self, data):
        # ========================= This Part of code only for if user wish to save card from portal side =====================
        optional_save_token_request = False
        if 'save_token_request' in data:
            optional_save_token_request = data.get('save_token_request')
        # =========================================xxxxxxxxxxxxxxxxxxxxxxx===============================================

        data['actual_total'] = data.get('charge_total')
        data, invoice_payment = get_invoice_flag(data)
        _logger.info("\ninvoice_payment--->"+str(invoice_payment))

        AccMove = self.env['account.move'].sudo()
        ResPartner = self.env['res.partner'].sudo()
        href = request.params.get("window_href") or data.get(
            "window_href") or request.params.get("window_href")
        partner = ResPartner.search([('id', '=', int(data.get('partner_id')))])

        partner_name = ''
        if partner:
            partner_name = partner.name
            partner_name = partner_name.split(" ")[0] if partner_name else ''
            token_name = '**** **** ****' + data.get('last4')

        if data.get('invoice'):
            invoice = data.get('invoice')
            partner_name = invoice.partner_id.name.split(
                " ")[0] if invoice.partner_id.name else ''
            token_name = '**** **** ****' + data.get('last4')

        values = {
            'bamborachk_token_type': 'temporary',
            'bamborachk_token': data.get("token"),
            'provider_code': 'bamborachk',
            'provider_id': int(data.get('provider_id')),
            'provider_ref': 'bamborachk',
            'partner_id': data.get('partner_id'),
            'payment_details': token_name,
            'payment_method_id': int(data.get('pay_method')),
        }
        acq = self.env['payment.provider'].sudo().browse(int(data.get('provider_id')))

        if 'my/payment_method' in request.params.get("window_href") or optional_save_token_request:
            _logger.info("Customer Profile-->")
            profile_url = 'https://api.na.bambora.com/v1/profiles'
            pro_data = {
                "token": {
                    "name": partner_name,
                    "code": data.get("token")
                }
            }
            _logger.info(pro_data)
            srm = AppPayment(service_name='bambora_checkout', service_type='profile', service_key=acq.token)
            srm.data = pro_data
            response = srm.payment_process(company_id=acq.company_id.id)
            # response = requests.post(
            # pro_res = requests.post(profile_url, data=json.dumps(pro_data), headers=get_headers(
            #     data.get('bamborachk_merchant_id'), data.get('bamborachk_profile_api')))
            # _logger.info(pro_res.text)
            if response.get('error') == None or 'errors_message' not in response:
                pro_res = response
                if pro_res.get("code") == 1:
                    values['bamborachk_profile'] = response.get(
                        'customer_code')
                    values['bamborachk_token_type'] = 'permanent'
                else:
                    _logger.warning("Customer Profile: Failure")
                    raise ValidationError((response.get('message')))
            else:
                error = response.get('error') if 'error' in response else response.get("errors_message")
                raise ValidationError((error))

        _logger.info(values)
        PaymentMethod = self.env['payment.token'].sudo().create(values)
        _logger.info(PaymentMethod)
        return PaymentMethod

    def bamborachk_s2s_form_validate(self, data):
        _logger.info("bamborachk_s2s_form_validate")
        _logger.info(data)
        data['actual_total'] = data.get('charge_total')
        data, invoice_payment = get_invoice_flag(data)
        _logger.info("\ninvoice_payment--->"+str(invoice_payment))

        AccMove = self.env['account.move'].sudo()
        href = request.params.get("window_href") or data.get("window_href") or request.params.get("window_href")

        if '/payment_method' not in href:
            if data.get('order_id'):
                order = self.env['sale.order'].sudo().search(
                    [('id', '=', data.get('order_id'))])
                if order:
                    data['order_name'] = order.name
                    data['charge_total'] = order.amount_total
            if data.get('invoice'):
                invoice =  data.get('invoice')
                data['order_name'] = invoice.name
                data['charge_total'] = invoice.amount_total

        error = dict()
        mandatory_fields = ["provider_id", "provider_state",  "bamborachk_merchant_id", "bamborachk_payment_api", "bamborachk_profile_api", "order_name", "charge_total",
                            "code", "expiryMonth", "expiryYear", "last4", "token"]
        if 'my/payment_method' in request.params.get("window_href") or '/my/orders' in request.params.get("window_href"):
            mandatory_fields = ["provider_id", "provider_state",  "bamborachk_merchant_id", "bamborachk_payment_api",
                                "bamborachk_profile_api", "code", "expiryMonth", "expiryYear", "last4", "token"]
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        _logger.warning("ERROR" + str(error))
        return False if error else True


# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import re

from odoo import models, fields, api
from odoo.http import request
from odoo.exceptions import UserError
from odoo.service import common
from ..lib import mpgClasses
from datetime import datetime
import string
import random
import requests
import json
import pprint
import logging
import urllib.parse
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)
version_info = common.exp_version()
server_serie = version_info.get('server_serie')

TRANSACTION_CODES = {
    "00": "PURCHASE",
    "01": "PRE-AUTHORIZATION",
    "06": "CARD-VERIFICATION",
}

ELECTRONIC_COMMERCE_INDICATOR = {
    "5": "Authenticated e-commerce transaction (3-D Secure)",
    "6": "Non-authenticated e-commerce transaction (3-D Secure)",
    "7": "SSL-enabled merchant",
}

RESULT = {
    "a": "Accepted",
    "d": "Declined",
}

CARD_TYPE = {
    "V": "Visa",
    "M": "Mastercard",
    "DC": "Diner's Card",
    "NO": "Novus/Discover",
    "D": "INTERAC® Debit",
    "C1": "JCB",
}

TRANSACTION_TYPES = [
    # ("preauthorization", "Preauthorization"),
    ("purchase", "Purchase"),
    ("cardverification", "Card Verification")
]

CVD_RESULT = {
    "1": "Success",
    "2": "Failed",
    "3": "Not performed",
    "4": "Card not eligible",
}

CONDITION = {
    "0": "Optional",
    "1": "Mandatory",
}

STATUS = [
    ("success", "Fraud tool successful"),
    ("failed", "Fraud tool failed (non-auto decision)"),
    ("disabled", "Fraud tool not performed"),
    ("ineligible", "Fraud tool was selected but card is not a credit card or card not eligibl"),
    ("failed_optional", "Fraud tool failed and auto decision is optional"),
    ("failed_mandatory", "Fraud tool failed auto decision is mandatory"),
]

DETAILS = [
    ("0", "Optional"),
    ("1", "Mandatory"),
]

FRAUD_TYPES = [
    ('cvd', 'CVD'),
    ('avs', 'AVS'),
    ('3d_secure', '3D Secure'),
    ('kount', 'Kount')
]

def remove_charandaccents(string):
    if string != None:
        return re.sub(r'[^ \nA-Za-z0-9/]+', '', string)
    else:
        return ''

def get_random_string(length):
    letters = string.ascii_lowercase
    result_str = ''.join(random.choice(letters) for i in range(length))
    return result_str


def get_url_id(href):
    url_id = False
    href = href.split("#")[1] if "#" in href else href.split("?")[1]
    vals = {}
    for item in href.split("&"):
        key, value = item.split("=")
        vals[key] = value
    return vals.get('id')


def url_to_dict(url_str):
    print(url_str)
    url_dict = urllib.parse.parse_qs(url_str)
    print("URL Params : " + str(url_dict))


def get_five_mins_ago(current_datetime):
    import datetime
    if isinstance(current_datetime, datetime.datetime):
        current_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    five_mins_ago = datetime.datetime.strptime(
        current_datetime, '%Y-%m-%d %H:%M:%S') - datetime.timedelta(minutes=5)
    return five_mins_ago.strftime('%Y-%m-%d %H:%M:%S')


def get_sale_lock(env):
    ICPSudo = env['ir.config_parameter'].sudo()
    sale_lock = ICPSudo.get_param('sale.group_auto_done_setting')
    return sale_lock


def get_href_params(request_object):
    # Extract the URL from the request object
    url = str(request_object).split()[1][1:-2]

    # Check if '?' exists in the URL
    url = url.split('?')[1] if '?' in url else url

    # Initialize an empty dictionary to store parameters
    href_params = {}

    # Split the URL by '&' to separate individual parameters
    for params in url.split('&'):
        # Split each parameter by '=' to get key and value
        key, value = params.split('=')

        # Add the key-value pair to the dictionary
        href_params[key] = value

    return href_params


class providerMoneris(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('monerischeckout', (
        'Moneris Checkout'))], ondelete={'monerischeckout': 'set default'})
    moneris_transaction_type = fields.Selection(
        string=('Moneris Transaction Type'),
        selection=TRANSACTION_TYPES,
        default='purchase',
        required=True)
    moneris_store_id = fields.Char(
        string='Store ID', help='Store Id in Moneris Direct Host Configuration')
    moneris_api_token = fields.Char(
        string='Api Token', help='Api Token in Moneris Direct Host Configuration')
    moneris_checkout_id = fields.Char()
    moneris_order_confirmation = fields.Selection(string='Moneris Order Confirmation', selection=[
        ('capture', ('Authorize & capture the amount and conform it'))], default='capture')
    moneris_store_card = fields.Selection(string='Store Card Data', selection=[
        ('never', 'Never'),
        ('customer', 'Let the customer decide'),
        ('always', 'Always')], default='never')
    # Payment Security
    moneris_avs = fields.Boolean(string='AVS', )
    moneris_avs_zip = fields.Boolean(string='Enable Zip', )
    moneris_cvv = fields.Boolean(string='CVV', default=True)
    moneris_3d_secure = fields.Boolean(string='3D Secure', )
    moneris_kount = fields.Boolean(string='Kount', )

    fees_active = fields.Boolean(default=False)
    fees_dom_fixed = fields.Float(default=0.35)
    fees_dom_var = fields.Float(default=3.4)
    fees_int_fixed = fields.Float(default=0.35)
    fees_int_var = fields.Float(default=3.9)

    allow_token_delete = fields.Boolean(
        string='Allow Token Delete',
        default=True,
        help='This field allows all users to delete other user `Payment Token`.'
    )

    moneris_token = fields.Boolean(string='Tokenization')
    moneris_lock_order = fields.Boolean(
        string='Lock Confirmed Sales',
        default=True,
    )
    moneris_recurring_invoice_scope = fields.Selection(
        selection=[
            ('overdue', 'Overdue invoices only'),
            ('all', 'All open invoices'),
        ],
        string='Recurring Invoice Scope',
        default='overdue',
        help='Select which invoices will be charged by the recurring payment scheduler.',
    )

    # @api.onchange('moneris_transaction_type')
    # def _onchange_moneris_transaction_type(self):
    #     for rec in self:
    #         if rec.moneris_transaction_type == 'cardverification':
    #             raise UserError(
    #                 ("Card Verification is not supported for this module. Please contact Development Team!"))
    @api.onchange("moneris_transaction_type")
    def onchange_saving_payment_methods(self):
        for rec in self:
            if rec.moneris_transaction_type == "06":
                rec.allow_tokenization = True

    @api.onchange("moneris_token")
    def onchange_saving_payment_token(self):
        for rec in self:
            if rec.code == "monerischeckout":
                if rec.moneris_token:
                    rec.allow_tokenization = True
                else:
                    rec.allow_tokenization = False

    def _get_s2s_moneris_urls(self, state):
        _logger.info(str(self) + "," + str(state))
        host = 'www3.moneris.com' if state == 'enabled' else 'esqa.moneris.com'
        return {'moneris_server_url': host}

    def _get_monerischeckout_urls(self, environment):
        environment = self._get_monerischeckout_environment()
        if environment == 'qa':
            host = 'https://gatewayt.moneris.com/chkt/request/request.php'
        if environment == 'prod':
            host = 'https://gateway.moneris.com/chkt/request/request.php'
        return {'moneris_chk_url': host}

    def _get_monerischeckout_environment(self):
        environment = 'qa' if self.state == 'test' else 'prod'
        return environment

    def _get_feature_support(self):
        res = super(providerMoneris, self)._get_feature_support()
        res['tokenize'].append('monerischeckout')
        return res

    def monerischeckout_compute_fees(self, amount, currency_id, country_id):
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

    # Moneris S2s Form Process Function
    @api.model
    def monerischeckout_s2s_form_process(self, data):
        PaymentToken = False
        acq = self.env['payment.provider'].sudo().search(
            [('id', '=', int(data.get('provider_id')))])
        href = data.get('formData', {}).get('window_href') or request.httprequest.url or request.params.get(
            'href') or request.params.get('window_href')
        if '/shop/payment' in href and acq.moneris_transaction_type != 'card_verification':
            raise UserError(
                ("You cannot add card using `Purchase` or 'Pre-Authorization`"))
        data_key = ''
        name = data.get('ticket_no')
        partner = self.env['res.partner'].sudo().search(
            [('id', '=', int(data.get('partner_id')))])
        partner_name = ''
        if partner:
            partner_name = partner.name
            partner_name = partner_name.split(" ")[0] if partner_name else ''

        values = {
            'moneris_profile': data_key,
            'name': name,
            'provider_ref': acq.code,
            'provider_id': int(data.get('provider_id')),
            'partner_id': int(data.get('partner_id')),
            'moneris_ticket': data.get('ticket_no'),
        }
        if data.get('ticket_no'):
            PaymentToken = self.env['payment.token'].sudo().search(
                [('moneris_ticket', '=', data.get('ticket_no'))])
            if not PaymentToken and acq.moneris_token:
                PaymentToken = self.env['payment.token'].sudo().create(values)
                _logger.info("PaymentToken--->" + str(PaymentToken))

        return PaymentToken

    # Moneris S2s Form Validate Function
    def monerischeckout_s2s_form_validate(self, data):
        error = dict()
        mandatory_fields = ["ticket_no", "provider_id", "partner_id"]
        for field_name in mandatory_fields:
            if not data.get(field_name):
                error[field_name] = 'missing'
        if error:
            _logger.warning(error)
        return False if error else True

    def monerischeckout_url_info(self, url):
        move_id = False
        url_dict = url_to_dict(url)
        return url_dict

    def _check_internal_user(self, partner_id=None):
        return self.env.user.has_group('os_payment.group_moneris_token_manager')

    def _get_moneris_recurring_invoices(self):
        self.ensure_one()
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
            ('payment_state', 'in', ('not_paid', 'partial')),
        ]
        if self.moneris_recurring_invoice_scope == 'overdue':
            today = fields.Date.context_today(self)
            domain += [('invoice_date_due', '!=', False), ('invoice_date_due', '<', today)]
        return self.env['account.move'].sudo().search(domain)

    def _process_moneris_recurring_invoices(self):
        self.ensure_one()
        invoices = self._get_moneris_recurring_invoices()
        remaining = len(invoices)
        for invoice in invoices:
            try:
                invoice._moneris_recurring_charge(self)
            except Exception:
                _logger.exception(
                    "Moneris recurring charge failed for invoice %s", invoice.id
                )
            finally:
                remaining -= 1
                self.env['ir.cron']._commit_progress(processed=1, remaining=remaining)

    @api.model
    def _cron_moneris_recurring_charge(self):
        providers = self.search([
            ('code', '=', 'monerischeckout'),
            ('state', '!=', 'disabled'),
        ])
        for provider in providers:
            provider._process_moneris_recurring_invoices()


class TxMoneris(models.Model):
    _inherit = 'payment.transaction'

    moneris_txn_type = fields.Char('Transaction type')
    moneris_customer_id = fields.Char('Customer Id')
    moneris_receipt_id = fields.Char('Receipt Id')
    moneris_response_code = fields.Char('Response Code')
    moneris_credit_card = fields.Char('Credit Card')
    moneris_card_name = fields.Char('Moneris Card Type')
    moneris_expiry_date = fields.Char('Expiry Date')
    moneris_transaction_time = fields.Char('Transaction Time')
    moneris_transaction_date = fields.Char('Transaction Date')
    moneris_transaction_id = fields.Char('Transaction ID')
    moneris_payment_type = fields.Char('Payment Type')
    # This information should be stored by the merchant
    moneris_reference_no = fields.Char('Reference Number')
    moneris_bank_approval = fields.Char('Bank Approval')
    moneris_card_holder = fields.Char('Cardholder')
    moneris_order_id = fields.Char('Response Order Id')
    moneris_iso_code = fields.Char('Iso Code')
    moneris_transaction_key = fields.Char('Transaction Key')
    moneris_transaction_no = fields.Char('Transaction Number')
    moneris_card_amount = fields.Char()
    moneris_cvd_result = fields.Char()
    moneris_avs_result = fields.Char()
    # Necessary for Payment Checkout
    moneris_card_type = fields.Char(string='Moneris Payment Method')
    moneris_gift_txntype = fields.Char("Txn Type")
    moneris_gift_cardnum = fields.Char("Gift Card Num")
    moneris_gift_refnum = fields.Char("Gift Ref Num")
    moneris_gift_orderno = fields.Char("Gift Order No")
    moneris_gift_txnnum = fields.Char("Gift Txn Num")
    moneris_rem_balance = fields.Char("Remaining Balance")
    moneris_gift_display = fields.Char("Gift Display")
    moneris_card_description = fields.Char("Card Desecription")
    moneris_gift_charge = fields.Char("Gift Charge")
    moneris_voucher_text = fields.Char("Voucher Text")
    gift_lines = fields.One2many('transaction.gift.lines', 'gift_id')
    # API Refund Fields
    moneris_auth_code = fields.Char()
    moneris_bank_totals = fields.Char()
    moneris_complete = fields.Char()
    moneris_corporate_card = fields.Char()
    moneris_is_visa_debit = fields.Char()
    moneris_ticket = fields.Char()
    moneris_response = fields.Text()
    moneris_fraud_lines = fields.One2many(
        'moneris.fraud.lines', 'transaction_id')

    # Moneris Card Transaction Convert

    def inline_card_convert(self, data, transaction):
        receipt = data.get('response').get('receipt')
        order_id = False
        # try:
        #     order_id = self.env['sale.order'].sudo().search(
        #         [('name', '=', data.get('response').get('request').get('order_no').split("/")[0])])
        # except Exception as e:
        #     raise e

        transaction['provider_reference'] = receipt.get(
            'cc', {}).get('reference_no')
        transaction['moneris_cvd_result'] = receipt.get(
            'cc', {}).get('cvd_result_code')
        # transaction['date'] = data.get('date') if data.get(
        #     'date') != False or 'null' else False
        # if receipt.get('cc', {}).get('transaction_date_time') and receipt.get('cc', {}).get('transaction_date_time') != 'null':
        #     dateTime = receipt.get('cc', {}).get('transaction_date_time')
        #     transaction['date'] = data.get(dateTime, fields.datetime.now())
        # transaction['partner_country_id'] = self.partner_id.country_id.id
        if receipt.get('result') == 'a':
            transaction['state'] = 'done'
        transaction['state_message'] = receipt.get('result')
        # transaction['type'] = "validation"
        # Moneris Details
        card_name = receipt.get('cc', {}).get('card_type') or ''
        card_name = CARD_TYPE.get(card_name) or card_name
        transaction['moneris_card_name'] = card_name
        transaction['moneris_customer_id'] = receipt.get(
            'cc', {}).get('cust_id') or ''
        transaction['moneris_receipt_id'] = receipt.get('ReceiptId') or ''
        transaction['moneris_response_code'] = receipt.get(
            'cc', {}).get('response_code') or ''
        transaction['moneris_credit_card'] = receipt.get(
            'cc', {}).get('first6last4') if receipt.get('cc') else ''
        transaction['moneris_expiry_date'] = receipt.get(
            'cc', {}).get('expiry_date') if receipt.get('cc') else ''
        transaction['moneris_transaction_time'] = receipt.get(
            'cc', {}).get('transaction_date_time', '').split(" ")[0] or ''
        transaction['moneris_transaction_date'] = receipt.get(
            'cc', {}).get('transaction_date_time', '').split(" ")[1] or ''
        transaction['moneris_payment_type'] = receipt.get('PaymentType') or ''
        transaction['moneris_reference_no'] = receipt.get(
            'cc', {}).get('reference_no')
        transaction['moneris_bank_approval'] = receipt.get(
            'cc', {}).get('approval_code') or ''
        transaction['moneris_card_holder'] = receipt.get(
            'cc', {}).get('cust_id') or ''
        transaction['moneris_order_id'] = receipt.get(
            'cc', {}).get('order_no') or ''
        transaction['moneris_iso_code'] = receipt.get(
            'cc', {}).get('iso_response_code') or ''
        transaction['moneris_transaction_key'] = ''
        transaction['moneris_transaction_no'] = receipt.get(
            'cc', {}).get('transaction_no') or ''
        transaction['moneris_card_amount'] = receipt.get(
            'cc', {}).get('amount') or ''
        transaction['moneris_card_type'] = 'Card'
        return transaction

    def _monerischeckout_convert_transaction(self, data):
        try:
            transaction = {}
            if data.get('response', {}).get('receipt', {}).get('cc'):
                transaction.update(self.inline_card_convert(data, transaction))
            if data.get('response', {}).get('receipt', {}).get('gift'):
                transaction.update(
                    self.monerischeckout_gift_convert(data, transaction))
            return transaction
        except Exception as e:
            return {'error': str(e.args)}

    def monerischeckout_gift_convert(self, data, transaction):
        required_values = {}
        try:
            receipt = data.get('response').get('receipt')
            required_values['moneris_card_type'] = 'Gift with Card'
            for gift in receipt.get('gift', []):
                gift.update({'gift_id': self.id})
                gifts = self.env['transaction.gift.lines'].create(gift)
                self.gift_lines = gifts.ids

            if not receipt.get('cc') and receipt.get('gift'):
                required_values['moneris_card_type'] = 'Gift Card'

            # if receipt.get('gift') and not receipt.get('cc'):
            #     if len(receipt.get('gift', [])) == 1:
            #         required_values = {
            #             'moneris_rem_balance': receipt.get('gift', [])[0].get('balance_remaining', ''),
            #             'moneris_gift_txntype': data.get('TransType', ''),
            #             'moneris_gift_cardnum': receipt.get('gift', [])[0].get('first6last4', ''),
            #             'moneris_gift_orderno': receipt.get('gift', [])[0].get('order_no', ''),
            #             'moneris_gift_refnum': receipt.get('gift', [])[0].get('reference_no', ''),
            #             'moneris_gift_charge': receipt.get('gift', [])[0].get('transaction_amount', ''),
            #             'moneris_gift_txnnum': receipt.get('gift', [])[0].get('transaction_no', ''),
            #         }
            #         required_values['provider_reference'] = receipt.get('gift', [])[
            #             0].get('reference_no')
            #         if receipt.get('gift', [])[0].get('result') == 'a':
            #             required_values['state'] = 'done'
            #             required_values['state_message'] = receipt.get('gift', [])[
            #                 0].get('result')
            #             # required_values['type'] = "validation"

            # transaction.update(required_values)
            return transaction
        except Exception as e:
            return {'error': str(e.args)}

    def _get_receipt(self, response):
        receipt = False
        if response:
            if response.get('response', {}):
                receipt = response.get(
                    'response', {}).get('receipt', {})
        return receipt

    def monerischeckout_refund_transaction(self, kwargs):
        _logger.info("MONERIS REFUND===>>>>>")
        context = dict(self._context)
        reference = self.reference or ''
        reference = reference.replace('Reversal of: ', '')
        reference = reference.split(",")[0] if len(
            reference.split(",")) > 1 else reference

        AccMove = self.env['account.move']
        move_id = AccMove.sudo().search([('name', '=', reference)])
        if move_id and move_id.payment_reference:
            environment = self.provider_id.environment if server_serie == '12.0' else self.provider_id.state
            moneris_url = self.provider_id._get_s2s_moneris_urls(
                environment)

            payment_reference = move_id.payment_reference
            _logger.info("reference---->" + str(reference))
            _logger.info("payment_reference---->" + str(payment_reference))

            PayTrx = self.env['payment.transaction']
            trx_id = PayTrx.sudo().search(
                [('reference', '=', payment_reference)])
            # store_id = self.provider_id.moneris_store_id
            # api_token = self.provider_id.moneris_api_token
            amount = str(self.amount)
            crypt_type = '7'
            dynamic_descriptor = ''
            cust_id = self.partner_id.name + '/' + str(self.partner_id.id)
            order_id = trx_id.moneris_order_id
            # For Refund, Completion and Purchase Correction transactions,
            # the order ID must be the same as that of the original transaction.

            txn_number = trx_id.moneris_transaction_no
            processing_country_code = self.provider_id.company_id.country_id.code or 'CA'
            status_check = False

            refund_req = mpgClasses.Refund(
                order_id, amount, crypt_type, txn_number)
            refund_req.setProcCountryCode(processing_country_code)
            refund_req.setTestMode(
                "_TEST") if environment == 'test' else refund_req.setTestMode("")

            if environment == 'test':
                refund_req.setTestMode(environment)

            refund = mpgClasses.mpgHttpsPost(
                moneris_url.get('moneris_server_url'),
                # store_id,
                # api_token,
                refund_req)
            refund.postRequest(self.provider_id)
            response = refund.getResponse()
            receipt = self._get_receipt(response=response)
            _logger.info("\nRefund Response-->\n" +
                         pprint.pformat(response))

            if receipt.get('ResponseCode') != 'null':
                _logger.info("ResponseCode" + str(receipt.get('ResponseCode')))
                if int(receipt.get('ResponseCode')) < 50:
                    _logger.info("REFUND SUCCESS")
                    card_name = receipt.get('CardType') or ''
                    card_name = CARD_TYPE.get(
                        card_name) or card_name

                    transaction = {
                        'moneris_auth_code': receipt.get('AuthCode'),
                        'moneris_bank_totals': receipt.get('BankTotals'),
                        'moneris_card_name': card_name,
                        'moneris_complete': receipt.get('Complete'),
                        'moneris_corporate_card': receipt.get('CorporateCard'),
                        'moneris_iso_code': receipt.get('ISO'),
                        'moneris_is_visa_debit': receipt.get('IsVisaDebit'),
                        'state_message': receipt.get('Message'),
                        'moneris_receipt_id': receipt.get('ReceiptId'),
                        'moneris_reference_no': receipt.get('ReferenceNum'),
                        'moneris_response_code': receipt.get('ResponseCode'),
                        'moneris_transaction_time': receipt.get('Ticket'),
                        'moneris_transaction_time': receipt.get('TimedOut'),
                        'moneris_card_amount': receipt.get('TransAmount'),
                        'moneris_transaction_date': receipt.get('TransDate'),
                        'moneris_transaction_id': receipt.get('TransID'),
                        'moneris_transaction_time': receipt.get('TransTime'),
                        'moneris_txn_type': receipt.get('TransType'),
                        'moneris_card_type': 'card',
                        'state': 'done',
                    }
                    _logger.info("\ntransaction--->" +
                                 pprint.pformat(transaction))
                    self.write(transaction)
                    return True

                else:
                    raise UserError(
                        ("Moneris Refund Failed Response--->" + str(receipt.get('Message'))))

            else:
                raise UserError(
                    ("Moneris Refund Error Response:\n" + str(receipt.get('Message'))))
        else:
            raise UserError(("Payment TrX reference not found"))

    def update_sale_order(self, order_id):
        sale_lock = self.provider_id.moneris_lock_order
        if order_id and order_id.state not in ['done', 'sale']:
            if order_id.amount_total == self.amount:
                order_id.action_confirm()
        if order_id and order_id.state not in ['done'] and sale_lock:
            order_id.action_done()

    def monerischeckout_s2s_do_transaction(self, kwargs):
        _logger.info(
            "\nmonerischeckout_s2s_do_transaction------>>>>\n" + pprint.pformat(kwargs))
        session = dict(request.session)
        # session = dict(request.session)
        gift_total = 0
        _logger.info("\n payment_id------>>>> %s" % (self.payment_id))
        _logger.info("\n payment_type------>>>> %s" % (self.payment_id.payment_type))
        if self.payment_id.payment_type == 'outbound':
            return self.monerischeckout_refund_transaction(kwargs)

        if not kwargs:
            if session.get('tx_kwargs') and session.get('tx_kwargs', {}).get(self.id):
                kwargs = session.get('tx_kwargs', {}).get(self.id)
                _logger.info("\nkwargs------>>>> %s" % (kwargs))

        if kwargs:
            # ============ If Declined ===============
            _logger.warning("TRANSACTION DECLINED")
            error_receipt = kwargs.get('response', {}).get('receipt', {})
            error_result = error_receipt.get('result')
            if error_result != 'a':
                state_message = "Declined" if error_receipt.get('result') == 'd' else ""
                # self.write({"state": "error", "state_message": state_message})
                self.moneris_update_failtx(kwargs)
                self._moneris_fraud_process(kwargs)
                self.token_id.write({'active': False, 'moneris_ticket': False})
                self._set_error(state_message)
                return False

        if kwargs and len(self) == 0:
            print("self ===>>>", self)
            response = kwargs.get('response')
            reference = response.get('request').get('order_no', '').rsplit(':')[0]
            print("reference ===>>>", reference)
            self = self.env['payment.transaction'].sudo().search([('reference', '=', reference)], limit=1)
            print("self ===>>>", self)

        self.ensure_one()
        res_json = {}
        AccMove = self.env['account.move']
        SaleOrder = self.env['sale.order']
        # Remove False Profile Before 5 minutes
        current_datetime = fields.Datetime.now()
        five_mins_ago = get_five_mins_ago(fields.Datetime.now())

        false_profiles = self.env['payment.token'].sudo().search(
            [('provider_id.code', '=', 'monerischeckout'), ('moneris_profile', 'in', (False, '')),
             ('create_date', '<', five_mins_ago)])
        for profile in false_profiles:
            profile.sudo().write({'active': False})

        # Receipt Request
        form_data = kwargs.get('formData', {})
        provider_id = form_data.get('provider_id') or kwargs.get('provider_id')
        ticket = kwargs.get('ticket')
        href = kwargs.get('formData', {}).get('window_href') or request.httprequest.url or request.params.get(
            'href') or request.params.get('window_href')
        acq = request.env['payment.provider'].sudo().search(
            [('id', '=', int(provider_id))])

        _logger.info("href--->" + str(href))
        _logger.info("kwargs--->" + str(kwargs))
        _logger.info("acq--->" + str(acq))

        if '/my/payment_method' in href or kwargs.get('card_tokenize') == True:
            self._monerischeckout_create_token(kwargs)
            res_json = kwargs
            result = kwargs.get('response', {}).get(
                'receipt', {}).get('result')
            _logger.info("Receipt Response===>>>" + str(res_json))
            if result == 'a':
                _logger.info("TRANSACTION APPROVED")
                transaction = {}
                transaction['state_message'] = result
                transaction['provider_reference'] = res_json.get(
                    'response', {}).get('receipt', {}).get('reference_no')
                if not self.provider_id.moneris_token:
                    self.token_id.write(
                        {'active': False, 'moneris_profile': False})
            else:
                _logger.warning("TRANSACTION DECLINED")
                state_message = "Declined" if result == 'd' else ""
                if  self.provider_id.moneris_token:
                    self.token_id.write(
                        {'active': False, 'moneris_profile': False})
                    self.moneris_update_failtx(res_json)
                    self._moneris_fraud_process(res_json)
                    self._set_error(state_message)
                return False

            res_json['formData'] = kwargs.get(
                'formData') if kwargs.get('formData') else {}


        elif '/shop/payment' in href or '/pay/sale' in href or '/my/orders' in href or (
                '/payment/pay' in href and 'sale_order_id' in href):
            response = False
            if self.provider_id.moneris_token:
                self._monerischeckout_create_token(kwargs)
            order_id = self.sale_order_ids[0] if len(
                self.sale_order_ids) > 0 else False
            if not order_id and session.get('sale_order_id'):
                order_id = session.get('sale_order_id')
                order_id = self.env['sale.order'].sudo().browse(int(order_id))
            if not order_id and ('/payment/pay' in href and 'sale_order_id' in href):
                import re
                match = re.search(r"sale_order_id=(\d+)", href.split("/payment/pay")[1].split("?")[1])
                order_id = match.group(1)
                order_id = self.env['sale.order'].sudo().browse(int(order_id))
                if not self.sale_order_ids:
                    self.sale_order_ids = order_id

            _logger.info("order_id ===>>> " + str(order_id))

            PayTrxn = self.env['payment.transaction'].sudo()
            domain = [('sale_order_ids', '=', order_id.id)]
            domain += [('state', '=', 'done')]
            domain += [('provider_id.code', '=', 'monerischeckout')]
            domain += [('id', 'not in', self.ids)]
            gift_txns = PayTrxn.search(domain)

            paid_amt = 0
            for gift_txn in gift_txns:
                for gift_line in gift_txn.gift_lines:
                    paid_amt += float(gift_line.transaction_amount)

            trnx_amt = float(self.amount) - float(paid_amt)
            session = request.session or {}
            self._mc_process_session(session, gift_total, order_id)
            print("trnx_amt===>>>" + str(trnx_amt))

            if trnx_amt > 0 and self.provider_id.moneris_transaction_type == 'cardverification':
                response = self._monerischeckout_sale_purchase(
                    trnx_amt, paid_amt, order_id)
                if response:
                    return response

            if self.provider_id.moneris_transaction_type != 'cardverification':
                res_json = kwargs
                ##########################################################################
                res_json['formData'] = kwargs.get(
                    'formData') if kwargs.get('formData') else {}
                sale_tx = self._monerischeckout_process_saletx(kwargs)
                if not sale_tx:
                    return sale_tx
                ##########################################################################


        elif '/my/invoices' in href or '/invoice/pay' in href or ('/payment/pay' in href and 'invoice_id' in href):
            print("'/my/invoices' in href or '/invoice/pay' in href")
            if self.provider_id.moneris_token:
                self._monerischeckout_create_token(kwargs)
            account_invoice_id = self.invoice_ids if len(
                self.invoice_ids) > 0 else False
            if not account_invoice_id:
                invoice_id = href.split(
                    '/invoice/pay/')[1].split('/')[0] if '/invoice/pay' in href else href.split(
                    '/my/invoices/')[1].split('?')[0]
                if invoice_id:
                    account_invoice_id = self.env['account.move'].sudo().search(
                        [('id', '=', invoice_id)], limit=1)

            _logger.info("account_invoice_id ===>>> " +
                         str(account_invoice_id))

            PayTrxn = self.env['payment.transaction'].sudo()
            domain = [('invoice_ids', '=', account_invoice_id.id)]
            domain += [('state', '=', 'done')]
            domain += [('provider_id.code', '=', 'monerischeckout')]
            domain += [('id', 'not in', self.ids)]
            gift_txns = PayTrxn.search(domain)

            paid_amt = 0
            for gift_txn in gift_txns:
                for gift_line in gift_txn.gift_lines:
                    paid_amt += float(gift_line.transaction_amount)

            trnx_amt = float(self.amount) - float(paid_amt)
            PayTrxn = self.env['payment.transaction'].sudo()
            tx_domain = [('invoice_ids', '=', account_invoice_id.id)]
            tx_domain += [('state', '=', 'done')]
            tx_domain += [('provider_id.code', '=', 'monerischeckout')]
            tx_domain += [('id', 'not in', self.ids)]
            tx_domain += [('amount', '=', 0.00)]
            card_verify_txn = PayTrxn.search(tx_domain)

            print("card_verify_txn ===>>>", card_verify_txn)
            if card_verify_txn and card_verify_txn.amount == 0.00:
                card_verify_txn.unlink()
            self._mc_process_session(
                request.session or {}, gift_total, account_invoice_id)

            print("trnx_amt===>>>" + str(trnx_amt))
            if trnx_amt > 0 and self.provider_id.moneris_transaction_type == 'cardverification':
                response = self._monerischeckout_invoice_Pay(account_invoice_id, trnx_amt, paid_amt, href)
                return response

            if self.provider_id.moneris_transaction_type != 'cardverification':
                res_json = kwargs
                result = res_json.get('response', {}).get(
                    'receipt', {}).get('result')
                _logger.info("Invoice Receipt Response" + str(res_json))
                if result == 'a':
                    _logger.info("TRANSACTION APPROVED")
                    transaction = {}
                    transaction['state_message'] = result
                    transaction['provider_reference'] = res_json.get(
                        'response', {}).get('receipt', {}).get('reference_no')
                    self._moneris_fraud_process(res_json)
                    if not self.provider_id.moneris_token:
                        self.token_id.write(
                            {'active': False, 'moneris_ticket': False})

                else:
                    _logger.warning("TRANSACTION DECLINED")
                    receipt = res_json.get('response', {}).get('receipt', {})
                    state_message = "Declined" if receipt.get(
                        'result') == 'd' else ""
                    self.write(
                        {"state": "error", "state_message": state_message})
                    self.token_id.write(
                        {"active": False}) if self.token_id.active == True else None
                    self.moneris_update_failtx(res_json)
                    self._moneris_fraud_process(res_json)
                    self.token_id.write(
                        {'active': False, 'moneris_ticket': False})
                    return False

                if kwargs.get('formData'):
                    res_json['formData'] = kwargs.get('formData')

        else:
            context = dict(self._context)
            _logger.warning("context===>>>" + str(context))

            if '/my/orders/' not in href:
                _logger.info("'/my/orders/ not in href'")
                if 'my/invoices/' in href:
                    move_id = href.split(
                        '/my/invoices/')[1].split("?")[0].replace('/transaction/token', '')
                    model = 'account.move'
                if 'invoice/pay/' in href:
                    model = 'account.move'
                    move_id = href.split(
                        '/invoice/pay/')[1].split("/")[0].replace('/s2s_token_tx/', '')
                # ------------------------------------
                if '/website_payment' in href or '/payment/pay' in href:
                    try:
                        href_params = get_href_params(href)
                    except Exception as e:
                        href_params = get_href_params(
                            request.params.get('window_href'))

                    model = 'sale.order'
                    domain = [('code', '=', 'sale.order')]
                    domain += [('active', '=', True)]
                    order_id = None
                    sale_seq = request.env['ir.sequence'].sudo().search(
                        domain, limit=1)
                    if href_params.get('reference') and sale_seq.prefix in href_params.get('reference'):
                        sale_domain = [
                            ('name', '=', href_params.get('reference'))]
                        sale_domain += [('id', '=',
                                         href_params.get('order_id'))]
                        order_id = request.env['sale.order'].sudo().search(
                            sale_domain)
                    if not order_id or href_params.get('invoice_id'):
                        model = 'account.move'
                        move_id = href_params.get('invoice_id')
                # ------------------------------------
                else:
                    model = context.get('active_model') or context.get(
                        'params', {}).get('model')
                    move_id = context.get('active_id') or context.get('active_ids')[
                        0] or context.get('params', {}).get('id')

                data_request = {}
                environment = self.provider_id._get_monerischeckout_environment()
                url = self.provider_id._get_monerischeckout_urls(
                    environment).get('moneris_chk_url')

                ticket = kwargs.get(
                    'ticket') or self.token_id.moneris_profile if self.token_id.moneris_profile else self.token_id.name
                data_request = {
                    # "store_id": self.provider_id.moneris_store_id,
                    # "api_token": self.provider_id.moneris_api_token,
                    # "checkout_id": self.provider_id.moneris_checkout_id,
                    "ticket": ticket,
                    "environment": environment,
                    "action": "receipt"
                }
                srm = AppPayment(service_name='moneris', service_type='receipt', service_key=self.provider.token)
                srm.data = data_request
                response = srm.payment_process(company_id=acq.company_id.id)
                # response = requests.post(url, data=json.dumps(data_request))

                tree = response.json()
                result = tree.get('response', {}).get(
                    'receipt', {}).get('result')
                _logger.info("Receipt Response" + str(tree))
                if result == 'a':
                    _logger.info("TRANSACTION APPROVED")
                    transaction = {}
                    transaction['state_message'] = result
                    transaction['provider_reference'] = tree.get(
                        'response', {}).get('receipt', {}).get('reference_no')
                    if '/website_payment' in href  or '/payment/pay' in href:
                        res_json = response.json()
                    if not self.provider_id.moneris_token:
                        self.token_id.write(
                            {'active': False, 'moneris_ticket': False})
                else:
                    _logger.warning("TRANSACTION DECLINED")
                    self.token_id.write(
                        {'active': False, 'moneris_ticket': False})
                    receipt = res_json.get('response', {}).get('receipt', {})
                    state_message = "Declined" if receipt.get('result') == 'd' else ""
                    self.moneris_update_failtx(res_json)
                    self._moneris_fraud_process(res_json)
                    self._set_error(state_message)
                    return False

                # Update the Token
                if kwargs.get('formData'):
                    tree['formData'] = kwargs.get('formData')

                tx = self
                token = self.token_id
                self._monerischeckout_update_token(tree, tx, href, token)
                # -----New addition
                if model == 'account.move' and self.token_id.moneris_profile and self.provider_id.moneris_transaction_type == 'card_verification':
                    """Make a s2s Purchase with the Token"""
                    _logger.info("""Make a s2s Purchase with the Token""")

                    type_of = 'res_purchase_cc'
                    data_key = self.token_id.moneris_profile
                    move_id = AccMove.browse(int(move_id))
                    order_id = move_id.name + '/' + get_random_string(4)
                    cust_id = move_id.partner_id.name + '/' + str(move_id.id)
                    amount = str(move_id.amount_residual)
                    pan = ''
                    expdate = ''
                    crypt_type = '7'
                    dynamic_descriptor = ''
                    processing_country_code = self.provider_id.company_id.country_id.code
                    environment = self.provider_id.environment if server_serie == '12.0' else self.provider_id.state
                    moneris_url = self.provider_id._get_s2s_moneris_urls(
                        environment)
                    pur_req = mpgClasses.PurchaseVault(
                        type_of, data_key, order_id, cust_id, amount, pan, expdate, crypt_type, dynamic_descriptor)
                    pur_req.setProcCountryCode(processing_country_code)
                    pur_req.setTestMode(
                        "_TEST") if environment == 'test' else pur_req.setTestMode("")
                    purchase = mpgClasses.mpgHttpsPost(
                        moneris_url.get('moneris_server_url'),
                        # self.provider_id.moneris_store_id,
                        # self.provider_id.moneris_api_token,
                        pur_req)
                    purchase.postRequest(self.provider_id)
                    response = purchase.getResponse()
                    _logger.info("\nPurchase Vault Response-->\n" +
                                 pprint.pformat(response))
                    res_json = response
                    self._process_s2s_purchase_response(move_id, response)

            if '/my/orders/' in href:
                model = 'sale.order'
                sale_id = href.split(
                    '/my/orders/')[1].split("?")[0].replace('/transaction/token', '')

                if model == 'sale.order' and not self.token_id.moneris_profile:
                    data_request = {}
                    environment = self.provider_id._get_monerischeckout_environment()
                    url = self.provider_id._get_monerischeckout_urls(
                        environment).get('moneris_chk_url')

                    _logger.info("\nenvironment===>>> " + str(environment) +
                                 "\nurl===>>> " + str(url))

                    ticket = kwargs.get(
                        'ticket') or self.token_id.moneris_profile or self.token_id.name
                    data_request = {
                        # "store_id": self.provider_id.moneris_store_id,
                        # "api_token": self.provider_id.moneris_api_token,
                        # "checkout_id": self.provider_id.moneris_checkout_id,
                        "ticket": ticket,
                        "environment": environment,
                        "action": "receipt"
                    }
                    srm = AppPayment(service_name='moneris', service_type='receipt', service_key=self.provider.token)
                    srm.data = data_request
                    response = srm.payment_process(company_id=acq.company_id.id)
                    # response = requests.post(
                    #     url, data=json.dumps(data_request))

                    tree = response.json()
                    result = tree.get('response', {}).get(
                        'receipt', {}).get('result')
                    _logger.info("Receipt Response" + str(tree))
                    if result == 'a':
                        _logger.info("TRANSACTION APPROVED")
                        transaction = {}
                        transaction['state_message'] = result
                        transaction['provider_reference'] = tree.get(
                            'response', {}).get('receipt', {}).get('reference_no')

                        # -----------------------------
                        order_id = self.env['sale.order'].sudo().browse(
                            int(sale_id))
                        if order_id:
                            order_id.update_sale_order()
                        # -----------------------------
                        if not self.provider_id.moneris_token:
                            self.token_id.write(
                                {'active': False, 'moneris_ticket': False})

                    else:
                        _logger.warning("TRANSACTION DECLINED")
                        return False

                    # Update the Token
                    if kwargs.get('formData'):
                        tree['formData'] = kwargs.get('formData')

                    tx = self
                    token = self.token_id
                    self._monerischeckout_update_token(tree, tx, href, token)
                    # -----New addition

                if model == 'sale.order' and self.token_id.moneris_profile:
                    """Make a s2s Purchase with the Token"""
                    _logger.info("""Make a s2s Purchase with the Token""")

                    type_of = 'res_purchase_cc'
                    data_key = self.token_id.moneris_profile
                    order = SaleOrder.browse(int(sale_id))
                    order_id = order.name + '/' + get_random_string(4)
                    cust_id = order.partner_id.name + '/' + str(order.id)
                    amount = str(order.amount_total)
                    pan = ''
                    expdate = ''
                    crypt_type = '7'
                    dynamic_descriptor = ''
                    processing_country_code = self.provider_id.company_id.country_id.code
                    environment = self.provider_id.environment if server_serie == '12.0' else self.provider_id.state
                    moneris_url = self.provider_id._get_s2s_moneris_urls(
                        environment)
                    pur_req = mpgClasses.PurchaseVault(
                        type_of, data_key, order_id, cust_id, amount, pan, expdate, crypt_type, dynamic_descriptor)
                    pur_req.setProcCountryCode(processing_country_code)
                    pur_req.setTestMode(
                        "_TEST") if environment == 'test' else pur_req.setTestMode("")
                    purchase = mpgClasses.mpgHttpsPost(
                        moneris_url.get('moneris_server_url'),
                        # self.provider_id.moneris_store_id,
                        # self.provider_id.moneris_api_token,
                        pur_req)
                    purchase.postRequest(self.provider_id)
                    response = purchase.getResponse()
                    _logger.info("\nPurchase Vault Response-->\n" +
                                 pprint.pformat(response))

                    self._process_s2s_purchase_response(order, response)
                else:
                    _logger.warning("Empty moneris_profile===>>>" +
                                    str(self.token_id.moneris_profile))

        return self._monerischeckout_s2s_validate_tree(res_json)

    def _monerischeckout_s2s_validate_tree(self, tree):
        return self._monerischeckout_s2s_validate(tree)

    def _monerischeckout_s2s_validate(self, tree):
        print("_monerischeckout_s2s_validate")
        token = self.token_id
        href = tree.get('formData', {}).get('window_href') or request.httprequest.url or request.params.get(
            'href') or request.params.get('window_href')
        if href == None:
            if tree.get('formData'):
                href = tree.get('formData', {}).get('window_href')
        _logger.info("s2s_validate: href------>>>>" + str(href))
        _logger.info("s2s_validate: tree------>>>>" + str(tree))
        result = False

        tx = self
        if 'response' in tree:
            if 'receipt' in tree['response']:
                receipt = tree['response']['receipt']
                if receipt.get('cc', {}).get('transaction_code'):
                    transaction_code = receipt.get(
                        'cc', {}).get('transaction_code')
                    _logger.info("TRASACTION TYPE--->" +
                                 str(TRANSACTION_CODES.get(transaction_code)))

                if self.provider_id.moneris_transaction_type != 'card_verification':
                    if tree.get('response', {}).get('success') == 'true':
                        order_id = False
                        self._monerischeckout_receipt_check(tree, tx, href)
                        self._monerischeckout_update_token(
                            tree, tx, href, token)

                        if '/my/invoices/' in href or '/pay/invoice' in href:
                            invoice_id = href.split(
                                '/my/invoices/')[1].split('?')[0]
                            move_id = self.env['account.move'].sudo().browse(
                                int(invoice_id))
                            # if '/my/invoices/' in href and self.state == "done":
                            #     self._reconcile_after_done()
                        if '/pay/invoice' in href:
                            invoice_id = href.split(
                                '/pay/invoice')[1].split('?')[0]
                            move_id = self.env['account.move'].sudo().browse(
                                int(invoice_id))

                        # if '/shop/payment' in href or '/my/orders' in href:
                        #     if len(self.sale_order_ids) > 0:
                        #         self.sale_order_ids[0].action_confirm()
                        #         if self.provider_id.moneris_lock_order:
                        #             self.sale_order_ids[0].action_done()

                        if '/website_payment' in href or '/payment/pay' in href:
                            if '&' in href:
                                href_params = get_href_params(href)
                            else:
                                href.split(
                                    '/website_payment/token')[1].split('/')
                                try:
                                    href_params = {}
                                    href_params['verison'] = href.split(
                                        '/website_payment/token')[1].split('/')[1]
                                    href_params['amount_total'] = href.split(
                                        '/website_payment/token')[1].split('/')[2]
                                    href_params['currency_id'] = href.split(
                                        '/website_payment/token')[1].split('/')[3]
                                    href_params['reference'] = href.split(
                                        '/website_payment/token')[1].split('/')[4]
                                    href_params['partner_id'] = href.split(
                                        '/website_payment/token')[1].split('/')[5]
                                except Exception as e:
                                    _logger.warning("Error %s", e.args)
                            order = href_params.get('order_id')
                            model = 'sale.order'
                            domain = [('code', '=', 'sale.order')]
                            domain += [('active', '=', True)]
                            sale_seq = request.env['ir.sequence'].sudo().search(
                                domain, limit=1)
                            if href_params.get('reference') and sale_seq.prefix in href_params.get('reference'):
                                sale_domain = [
                                    ('name', '=', href_params.get('reference'))]
                                sale_domain += [('id', '=',
                                                 href_params.get('order_id'))]
                                order_id = request.env['sale.order'].sudo().search(
                                    sale_domain)
                            if not order_id or href_params.get('invoice_id'):
                                model = 'account.move'
                                invoice_id = href_params.get('invoice_id')
                                order_id = request.env[model].sudo().search(
                                    [('id', '=', invoice_id)])

                            if order_id and model != 'account.move':
                                _logger.info(
                                    "order_id ===>>> " + str(order_id))
                                self.update_sale_order(order_id)

                        result = True  # =========>>>>>>>>>
                    else:
                        status = receipt.get('Message').replace("/n", "")
                        error = 'Received unrecognized status for Moneris s2s payment %s: %s, set as error' % (
                            tx.reference, status)
                        _logger.info(error)
                        tx.write({
                            'state': 'error',
                            'state_message': str(receipt.get('Message')).replace("\n", ""),
                            'provider_reference': receipt.get('ReferenceNum') if receipt.get(
                                'ReferenceNum') != 'null' else False,
                        })
                        result = False

                if self.provider_id.moneris_transaction_type == 'card_verification':
                    if receipt.get('ResponseCode', {}):
                        if int(receipt.get('ResponseCode', {})) < 50:
                            tx.write({
                                'state': 'done',
                                'state_message': str(receipt.get('Message')).replace("\n", ""),
                                'provider_reference': receipt.get('ReferenceNum') if receipt.get(
                                    'ReferenceNum') != 'null' else False,
                            })

                            context = dict(self._context)
                            if '/my/orders/' not in href:
                                _logger.info("'/my/orders/ not in href'")
                                if '/website_payment' in href or '/payment/pay' in href:
                                    href_params = get_href_params(href)
                                    order = href_params.get('order_id')
                                    domain = [('code', '=', 'sale.order')]
                                    domain += [('active', '=', True)]
                                    sale_seq = request.env['ir.sequence'].sudo().search(
                                        domain, limit=1)
                                    if href_params.get('reference') and sale_seq.prefix in href_params.get('reference'):
                                        sale_domain = [
                                            ('name', '=', href_params.get('reference'))]
                                        sale_domain += [('id', '=',
                                                         href_params.get('order_id'))]
                                        order_id = request.env['sale.order'].sudo().search(
                                            sale_domain)
                                        self.update_sale_order(order_id)
                                    if not order_id or href_params.get('invoice_id'):
                                        model = 'account.move'
                                        invoice_id = href_params.get(
                                            'invoice_id')
                                        order_id = request.env[model].sudo().search(
                                            [('id', '=', invoice_id)])

                                if 'my/invoices/' in href:
                                    move_id = href.split(
                                        '/my/invoices/')[1].split("?")[0].replace('/transaction/token', '')
                                    model = 'account.move'
                                if 'invoice/pay/' in href:
                                    model = 'account.move'
                                    move_id = href.split(
                                        '/invoice/pay/')[1].split("/")[0].replace('/s2s_token_tx/', '')
                                else:
                                    model = context.get('active_model') or context.get(
                                        'params', {}).get('model')
                                    move_id = context.get('active_id') or context.get('active_ids')[
                                        0] or context.get('params', {}).get('id')
                            if '/shop/payment' in href or '/my/orders' in href:
                                model = 'sale.order'
                                session = dict(request.session)
                                order_id = self.sale_order_ids[0] if len(
                                    self.sale_order_ids) > 0 else False
                                if not order_id and session.get('sale_order_id'):
                                    order_id = session.get('sale_order_id')
                                    order_id = self.env['sale.order'].sudo().browse(
                                        int(order_id))

                                if order_id:
                                    _logger.info(
                                        "order_id ===>>> " + str(order_id))
                                    self.update_sale_order(order_id)
                            # ----------------------------------------------------------------------------------------------

        else:
            print("No response in tree")
        # result = tree if '/my/payment_method' in href or '/shop/payment' in href else result
        # result = tree if '/my/orders' in href or '/pay/sale' in href else result
        result = tree if '/my/payment_method' in href or '/shop/payment' in href else result
        return result

    def _monerischeckout_process_saletx(self, kwargs):
        res_json = kwargs
        result = kwargs.get('response', {}).get('receipt', {}).get('result')
        _logger.info("Receipt Response===>>>" + str(res_json))
        if result == 'a':
            _logger.info("TRANSACTION APPROVED")
            transaction = {}
            transaction['state_message'] = result
            transaction['provider_reference'] = res_json.get(
                'response', {}).get('receipt', {}).get('cc', {}).get('reference_no')
            self._moneris_fraud_process(res_json)
            # self.sudo().with_context({'user_id':1})._set_done()
            if not self.provider_id.moneris_token:
                self.token_id.write(
                    {'active': False, 'moneris_profile': False})
            #############################################################################
            #############################################################################
            ICPSudo = self.env['ir.config_parameter'].sudo()
            automatic_invoice = ICPSudo.get_param('sale.automatic_invoice')
            group_auto_done = ICPSudo.get_param('sale.group_auto_done_setting')
            _logger.info("automatic_invoice ===>>> %s", automatic_invoice)
            _logger.info("group_auto_done ===>>>%s", group_auto_done)
            print("8888888888888888888888888888888888888")
            try:
                if group_auto_done and self.sale_order_ids[0].state != "done":
                    self.sale_order_ids[0].sudo().with_context(
                        {'user_id': 1}).action_done()
                if len(self.sale_order_ids) > 0 and len(self.invoice_ids) == 0 and not group_auto_done:
                    if self.sale_order_ids[0].amount_total == self.amount:
                        self.sale_order_ids[0].sudo().with_context(
                            {'user_id': 1}).action_confirm()

                # res = self._monerischt_card_convert(self.sale_order_ids[0],res_json.get(
                # 'response', {}).get('receipt', {}).get('cc', {}),{})
                self.write(transaction)
                self._set_done()

                if automatic_invoice:
                    self.sudo().with_context(
                        {'user_id': 1})._finalize_post_processing()
            except Exception as e:
                print("Excception ===>>>" + str(e.args))
            #############################################################################
            #############################################################################
            return True
        else:
            _logger.warning("TRANSACTION DECLINED")
            receipt = res_json.get('response', {}).get('receipt', {})
            state_message = "Declined" if receipt.get('result') == 'd' else ""
            # self.write({"state": "error", "state_message": state_message})
            self.moneris_update_failtx(res_json)
            self._moneris_fraud_process(res_json)
            self.token_id.write({'active': False, 'moneris_ticket': False})
            self._set_error(state_message)
            return False

    def _monerischeckout_invoice_Pay(self, account_invoice_id, trnx_amt, paid_amt, href):
        response = False
        is_subscription = False
        if 'invoice/transaction' in href and self.landing_route:
            if 'my/invoices' in self.landing_route:
                href = self.landing_route
        # if not request.session.sale_order_id:
        if self.reference:
            invoice_id = self.env['account.move'].sudo().search([("name", "=", self.reference)], limit=1)
            if invoice_id:
                account_invoice_id = invoice_id
        if '/my/invoices' in href or '/pay/invoices' in href:
            move_id = href.split('/my/invoices/')[1].split('?')[0]
            account_invoice_id = self.env['account.move'].sudo().browse(int(move_id))

        if '/shop/payment' in href or '/pay/sale' in href or '/my/orders' in href or '/payment/pay' in href or '/payment/transaction' in href:
            # if ('invoice_id' in request.params and request.params.get('invoice_id')):
            #     account_invoice_id=self.invoice_ids
            # if ('sale_order_id' in request.params and request.params.get('sale_order_id')):
            #     account_invoice_id = self.sale_order_ids
            if self.sale_order_ids:
                account_invoice_id = self.sale_order_ids
            elif self.invoice_ids:
                account_invoice_id = self.sale_order_ids
        if 'ir.cron' in href:
            if self.sale_order_ids:
                account_invoice_id = self.sale_order_ids
            elif self.invoice_ids:
                account_invoice_id = self.invoice_ids

        if "subscription_id" in self.invoice_ids.invoice_line_ids:
            subscription_record = self.invoice_ids.invoice_line_ids.filtered_domain([("subscription_id", "!=", False)])
            if subscription_record:
                account_invoice_id = self.invoice_ids
                is_subscription = True
        if self.payment_id.is_group_payment:
            order_name = self.reference
        else:
            order_name = account_invoice_id.name + '/' + get_random_string(
            4) if account_invoice_id.name else account_invoice_id.name + '/' + get_random_string(4)

        type_of = 'res_purchase_cc'
        data_key = self.token_id.moneris_profile
        cust_id = self.partner_id.name + \
                  '/' + str(self.invoice_ids.ids)  if self.payment_id.is_group_payment else account_invoice_id.partner_id.name + \
                  '/' + str(account_invoice_id.id)
        amount = str(trnx_amt)
        cust_id = remove_charandaccents(cust_id)
        pan = ''
        expdate = ''
        crypt_type = '7'
        dynamic_descriptor = ''
        processing_country_code = self.provider_id.company_id.country_id.code
        environment = self.provider_id.environment if server_serie in [
            '11.0', '12.0'] else self.provider_id.state
        moneris_url = self.provider_id._get_s2s_moneris_urls(
            environment)

        pur_req = mpgClasses.PurchaseVault(
            type_of, data_key, order_name, cust_id, amount, pan, expdate, crypt_type, dynamic_descriptor)
        pur_req.setProcCountryCode(processing_country_code)
        if environment == 'test':
            pur_req.setTestMode("_TEST")
        else:
            pur_req.setTestMode("")
        purchase = mpgClasses.mpgHttpsPost(
            moneris_url.get('moneris_server_url'),
            # self.provider_id.moneris_store_id,
            # self.provider_id.moneris_api_token,
            pur_req)
        purchase.postRequest(self.provider_id)
        response = purchase.getResponse()
        _logger.info("\nPurchase Vault Response-->\n" +
                     pprint.pformat(response))
        response = self._process_s2s_purchase_response(
            account_invoice_id, response)

        # if response and self.landing_route:
        #     if self.state == "done" and 'my/invoice' in self.landing_route:
        #         self._reconcile_after_done()
        if trnx_amt > 0 and paid_amt > 0:
            print("""Payment by Card and Gift Card""")
            if self.account_invoice_id:
                domain = [('account_invoice_id', 'in',
                           self.account_invoice_id.ids)]
                domain += [('state', '=', 'done')]
                domain += [('id', '!=', self.id)]
                txs = self.env['payment.transaction'].sudo().search(
                    domain)
                print("txns ===>>>> " + str(txs))
                txn_gift_amt = 0
                for txn in txs:
                    if txn.gift_lines:
                        for gift_line in txn.gift_lines:
                            txn_gift_amt += float(
                                gift_line.transaction_amount)
                    if txn.amount != txn_gift_amt:
                        txn.write({'amount': txn_gift_amt})

                domain = [('invoice_ids', '=',
                           self.account_invoice_id.id)]
                domain += [('state', '=', 'done')]
                paid_txns = self.env['payment.transaction'].sudo().search(
                    domain)
                paid_txns_amt = 0
                if len(paid_txns) > 1:
                    for paid_txn in paid_txns:
                        paid_txns_amt += paid_txn.amount

                if paid_txns_amt == self.invoice_ids.amount_total:
                    # self.write({'state': 'done'})
                    self._set_done()
                    # self._reconcile_after_done()

                    # sale_lock = get_sale_lock(self.env)
                    # if self.sale_order_id.state not in ['done', 'lock']:
                    #     self.sale_order_id.action_confirm()
                    # if sale_lock:
                    #     self.sale_order_id.action_done()

        # Subscription Payment done
        # if self.state == "done" and is_subscription:
        #     self._reconcile_after_done()

        return response

    def _monerischeckout_create_token(self, kwargs):
        try:
            tokenize = kwargs.get('response', {}).get('receipt', {}).get('cc', {}).get('tokenize')
            # tokenize = kwargs['response']['receipt']['cc']['tokenize']
            pay_token = self.env['payment.token'].sudo()
            token_id = pay_token.create({
                'provider_id': self.provider_id.id,
                'provider_ref': kwargs['response']['receipt']['cc']['order_no'],
                'payment_details': tokenize['first4last4'],
                'partner_id': self.partner_id.id,
                'moneris_profile': tokenize['datakey'],
                'moneris_ticket': kwargs['response']['request']['ticket'],
                'transaction_ids': self.ids,
                'payment_method_id': self.payment_method_id.id,

            })
            _logger.warning('token_id: ' + str(token_id))
            self.write({
                'token_id': token_id.id,
                'state': 'done'
            })
        except Exception as e:
            _logger.warning('Exception: ' + str(e.args))

    def _monerischeckout_receipt_check(self, tree, tx, href):
        receipt = tree.get('response').get('receipt')
        if receipt:
            if receipt.get('cc') and not receipt.get('gift'):
                _logger.info("Credit Card Only")
            if receipt.get('cc') and receipt.get('gift'):
                _logger.info("Credit Card and Gift Paid")
            if receipt.get('cc'):
                if type(receipt.get('cc', {}).get('result')) != str:
                    if int(receipt.get('cc', {}).get('result', {}).get('response_code')) < 50 and \
                            ('M' in receipt.get('cc', {}).get('cvd_result_code', '') or
                             'Y' in receipt.get('cc', {}).get('cvd_result_code', '')):
                        _logger.info(
                            'Validated Moneris s2s payment for tx %s: set as done' % (tx.reference))

                        if '/my/invoices/' not in href and '/my/payment_method' not in href:
                            if len(self.sale_order_ids) > 0:
                                if self.sale_order_ids[0].amount_total == self.amount:
                                    self.sale_order_ids[0].action_confirm()
                        date_time = receipt.get('cc', {}).get(
                            'transaction_date_time') or ''
                        receipt.update(state='done', date=receipt.get(
                            date_time, fields.Datetime.now()))
                        tranrec = self._monerischeckout_convert_transaction(
                            tree)
                        _logger.info(str("Transaction----->"))
                        _logger.info(tranrec)
                        tx.write(tranrec)
                        return True
                    else:
                        return False

                if type(receipt.get('cc', {}).get('result')) == str:
                    if receipt.get('cc', {}).get('response_code'):
                        if int(receipt.get('cc', {}).get('response_code')) < 50 and \
                                ('M' in receipt.get('cc', {}).get('cvd_result_code', '') or
                                 'Y' in receipt.get('cc', {}).get('cvd_result_code', '')):
                            _logger.info(
                                'Validated Moneris s2s payment for tx %s: set as done' % (tx.reference))
                            if '/my/invoices/' not in href and '/my/payment_method' not in href:
                                if len(self.sale_order_ids) > 0:
                                    self.sale_order_ids[0].sudo().write(
                                        {"state": "sale"})
                            date_time = receipt.get('cc', {}).get(
                                'transaction_date_time') or ''
                            receipt.update(state='done', date=receipt.get(
                                date_time, fields.Datetime.now()))
                            tranrec = self._monerischeckout_convert_transaction(
                                tree)
                            _logger.info(str("Transaction----->"))
                            _logger.info(tranrec)
                            tx.write(tranrec)
                            return True
                        else:
                            _logger.info(
                                'Validated Moneris s2s payment for tx %s: set as failure' % (tx.reference))
                            try:
                                raise UserError(receipt.get('cc', {}).get(
                                    'result', {}).get('message'))
                            except Exception as e:
                                pass
                            return False

            if not receipt.get('cc') and receipt.get('gift'):
                _logger.info("Only Gift Card")
                if int(receipt.get('gift', [])[0].get('response_code')) < 50:
                    _logger.info(
                        'Validated Moneris s2s payment for tx %s: set as done' % (tx.reference))
                    if '/my/invoices/' not in href:
                        if len(self.sale_order_ids) > 0:
                            if self.sale_order_ids[0].state != 'sale':
                                if self.sale_order_ids[0].amount_total == self.amount:
                                    self.sale_order_ids[0].sudo().action_confirm()
                    date_time = receipt.get('cc', {}).get(
                        'transaction_date_time') or ''
                    receipt.update(state='done')
                    tranrec = self._monerischeckout_convert_transaction(tree)
                    tranrec.update(state='done')
                    _logger.info(str("Transaction----->"))
                    _logger.info(tranrec)
                    response = tx.write(tranrec)
                    _logger.info(response)
                    return True
                else:
                    _logger.info(
                        'Validated Moneris s2s payment for tx %s: set as failure' % (tx.reference))
                    raise UserError(receipt.get('cc', {}).get(
                        'result', {}).get('message'))

    def _monerischeckout_update_token(self, tree, tx, href, token):
        if tree.get('response', {}).get('receipt', {}).get('cc', {}).get('tokenize'):
            tokenize = tree.get('response', {}).get(
                'receipt', {}).get('cc', {}).get('tokenize')

            name = tokenize.get('first4last4', '')
            if len(name) > 4:
                name = "**** **** **** %s" % (name[-4:])

            # TO DO: How to Check if token is temporary or permanent
            if tokenize.get('success') == 'true' and tokenize.get('status') == '001' and self.provider_id.moneris_token:
                _logger.info("Tokenize Object-->" + pprint.pformat(tokenize))
                token.write({
                    'moneris_profile': tokenize.get('datakey', ''),
                    'payment_details': name,
                    'moneris_ticket': tree.get('response', {}).get('request', {}).get('ticket', ''),
                })
            else:
                msg = """Token Not Created"""
                _logger.warning((msg))

    def monerischeckout_purchase_correction(self, kwargs):
        response = {}
        if kwargs.get('s2s_do_transaction'):
            if type(kwargs.get('s2s_do_transaction')) == bool:
                print("type(kwargs.get('s2s_do_transaction')) == bool")
            if type(kwargs.get('s2s_do_transaction')) != bool:
                if kwargs.get('s2s_do_transaction', {}).get('response'):
                    if kwargs.get('s2s_do_transaction', {}).get('response', {}).get('receipt', {}):
                        receipt = kwargs.get('s2s_do_transaction', {}).get(
                            'response', {}).get('receipt', {})
                        if receipt.get('cc', {}).get('transaction_code') and receipt.get('cc', {}).get(
                                'transaction_no'):
                            transaction_code = receipt.get(
                                'cc', {}).get('transaction_code')
                            transaction_no = receipt.get(
                                'cc', {}).get('transaction_no')

                            if TRANSACTION_CODES.get(transaction_code):
                                response = {
                                    "transaction_code": TRANSACTION_CODES.get(transaction_code)}
                                print(TRANSACTION_CODES.get(transaction_code))
                                if TRANSACTION_CODES.get(transaction_code) == "CARD-VERIFICATION":
                                    print("CARD-VERIFICATION")
                                else:
                                    print("""Other Transaction""")
                                    response = self.create_purchase_correction(
                                        kwargs, transaction_no)
                                    response = {
                                        "transaction_code": TRANSACTION_CODES.get(transaction_code),
                                        "success": response.get('success'),
                                        "response": response
                                    }

        return kwargs

    def moneris_update_failtx(self, res_json):
        receipt = res_json.get('response', {}).get('receipt', {})
        payment_vals = {}
        if receipt.get('cc', {}):
            cc = receipt.get('cc', {})
            payment_vals = {}
            payment_vals['moneris_txn_type'] = cc.get('transaction_type', "")
            payment_vals['moneris_customer_id'] = cc.get('cust_id', "")
            payment_vals['moneris_receipt_id'] = cc.get('card_type', "")
            payment_vals['moneris_response_code'] = cc.get('response_code', "")
            payment_vals['moneris_credit_card'] = cc.get('first6last4', "")
            payment_vals['moneris_card_name'] = cc.get('card_type', "")
            payment_vals['moneris_expiry_date'] = cc.get('expiry_date', "")
            if cc.get('transaction_date_time'):
                payment_vals['moneris_transaction_time'] = cc.get(
                    'transaction_date_time').split(" ")[0]
                payment_vals['moneris_transaction_date'] = cc.get(
                    'transaction_date_time').split(" ")[1]
            payment_vals['moneris_transaction_id'] = cc.get(
                'transaction_no', "")
            payment_vals['moneris_payment_type'] = cc.get(
                'transaction_type', "")
            payment_vals['moneris_reference_no'] = cc.get('reference_no', "")
            payment_vals['moneris_order_id'] = cc.get('order_no', "")
            payment_vals['moneris_iso_code'] = cc.get('iso_response_code', "")
            payment_vals['moneris_transaction_key'] = cc.get('card_type', "")
            payment_vals['moneris_transaction_no'] = cc.get(
                'transaction_no', "")
            payment_vals['moneris_card_amount'] = cc.get('amount', "")
            payment_vals['moneris_cvd_result'] = cc.get('cvd_result_code', "")
            payment_vals['moneris_avs_result'] = cc.get('avs_result_code', "")
        self.write(payment_vals)

    def create_purchase_correction(self, kwargs, transaction_no):
        """Create purchase_correction"""
        response = False
        PayTrx = self.env['payment.transaction']
        order_id = self.moneris_order_id
        if (self.sale_order_ids):
            cust_id = self.sale_order_ids[0].partner_id.id if self.sale_order_ids[0].partner_id else '' or ''
        total_amount = "{:.2f}".format(self.amount)
        txn_number = transaction_no or self.moneris_transaction_id
        crypt_type = "7"
        # String dynamic_descriptor = "123456";
        # String processing_country_code = "CA";
        # boolean status_check = false;

        environment = self.provider_id.state
        moneris_url = self.provider_id._get_s2s_moneris_urls(environment)
        correction_tx = mpgClasses.Correction(order_id, txn_number, crypt_type)
        correction_tx.setCorrectionAmount(total_amount)

        # host, store_id, api_token, trxn
        correction = mpgClasses.mpgHttpsPost(
            moneris_url.get('moneris_server_url'),
            # self.provider_id.moneris_store_id,
            # self.provider_id.moneris_api_token,
            correction_tx)

        request = correction.postRequest(self.provider_id)
        response = correction.getResponse()
        _logger.info("\ncorrection Response-->\n" + pprint.pformat(response))

        if response:
            if response.get('response', {}):
                if response.get('response', {}).get('receipt', {}):
                    receipt = response.get('response', {}).get('receipt', {})
                    if receipt.get('ResponseCode'):
                        if int(receipt.get('ResponseCode')) < 50:
                            _logger.info("""Code < 50: Transaction approved""")
                            card_name = receipt.get('CardType') or ''
                            card_name = CARD_TYPE.get(card_name) or card_name
                            corr_tx = PayTrx.sudo().create({
                                'provider_id': self.provider_id.id,
                                'amount': - self.amount,
                                'currency_id': self.currency_id.id,
                                'partner_id': self.partner_id.id,
                                'partner_country_id': self.partner_id.country_id.id,
                                'reference': 'Correction: ' + self.reference,
                                'state': 'done',
                                # 'type': 'server2server',
                                'token_id': self.token_id.id,
                                'moneris_receipt_id': receipt.get('ReceiptId'),
                                'moneris_reference_no': receipt.get('ReferenceNum'),
                                'moneris_response_code': receipt.get('ResponseCode'),
                                'moneris_iso_code': receipt.get('ISO'),
                                'moneris_auth_code': receipt.get('AuthCode'),
                                'moneris_transaction_time': receipt.get('TransTime'),
                                'moneris_transaction_date': receipt.get('TransDate'),
                                'moneris_card_amount': receipt.get('TransAmount'),
                                'moneris_card_name': card_name,
                                'moneris_transaction_id': receipt.get('TransID'),
                                'moneris_card_type': 'card',
                            })

                            _logger.info(
                                "Created Correction TX: %s" % (corr_tx))
                        else:
                            _logger.warning(
                                """Code >= 50: Transaction declined""")
                    else:
                        _logger.warning(
                            """NULL: Transaction was not sent for authorization""")
        return response

    def _process_s2s_purchase_response(self, move_id, tree):
        tx = self
        token = self.token_id
        _logger.info("token" + str(token))
        if tree.get('response', {}).get('receipt', {}):
            receipt = tree['response']['receipt']
            if receipt['Complete'] == 'true' and int(receipt['ResponseCode']) < 50:
                if int(receipt['ResponseCode']) < 50:
                    _logger.info(
                        'Validated Moneris s2s payment for tx %s: set as done' % (tx.reference))
                    date_time = ''
                    try:
                        date_time = receipt.get(
                            'TransDate') + ' ' + receipt.get('TransTime')
                    except Exception as e:
                        date_time = receipt.get('date_time')
                    receipt.update(state='done', date=receipt.get(
                        date_time, fields.Datetime.now()))
                    tranrec = self._monerischt_card_convert(
                        move_id, receipt, {})
                    _logger.info(str("\nTransaction\n----->") +
                                 pprint.pformat(tranrec))
                    tranrec.update({
                        'amount': self.amount
                    })
                    response = tx.write(tranrec)
                    _logger.info(str("response----->") + str(response))
                    return True
                else:
                    # =================================================================
                    # Send Email for Payment Unsuccessful
                    self._send_email_tx_failure(receipt)
                    # =================================================================
                    return False

            else:
                status = receipt.get('Message').replace("/n", "")
                error = 'Received unrecognized status for Moneris s2s payment %s: %s, set as error' % (
                    tx.reference, status)
                _logger.warning(error)
                tx.write({
                    'state': 'error',
                    'state_message': str(receipt.get('Message')).replace("\n", ""),
                    'provider_reference': receipt['ReferenceNum'],
                })
                context = self._context
                window_href = str(request.params.get(
                    'formData', {}).get('window_href'))
                if '/shop/payment' not in window_href:
                    model = context.get('active_model') or context.get(
                        'params', {}).get('model')
                    # move_id = context.get('active_id') or context.get('active_ids')[
                    #     0] or context.get('params', {}).get('id')
                    if model == 'account.move':
                        raise UserError(
                            ("Error Processing Moneris Transaction\n<b>Moneris Message:</b> " + str(status)))
                return False

    def _monerischeckout_sale_purchase(self, trnx_amt, paid_amt, order_id):
        response = False
        order_name = order_id.name + '/' + get_random_string(4)
        type_of = 'res_purchase_cc'
        data_key = self.token_id.moneris_profile
        cust_id = order_id.partner_id.name + '/' + str(order_id.id)
        amount = str(trnx_amt)
        pan = ''
        expdate = ''
        crypt_type = '7'
        dynamic_descriptor = ''
        processing_country_code = self.provider_id.company_id.country_id.code
        environment = self.provider_id.state
        moneris_url = self.provider_id._get_s2s_moneris_urls(environment)

        pur_req = mpgClasses.PurchaseVault(
            type_of, data_key, order_name, cust_id, amount, pan, expdate, crypt_type, dynamic_descriptor)
        pur_req.setProcCountryCode(processing_country_code)
        if environment == 'test':
            pur_req.setTestMode("_TEST")
        else:
            pur_req.setTestMode("")
        purchase = mpgClasses.mpgHttpsPost(
            moneris_url.get('moneris_server_url'),
            # self.provider_id.moneris_store_id,
            # self.provider_id.moneris_api_token,
            pur_req)
        purchase.postRequest(self.provider_id)
        response = purchase.getResponse()
        _logger.info("\nPurchase Vault Response-->\n" +
                     pprint.pformat(response))
        response = self._process_s2s_purchase_response(
            order_id, response)

        if trnx_amt > 0 and paid_amt > 0:
            print("""Payment by Card and Gift Card""")
            if self.sale_order_id:
                domain = [
                    ('sale_order_id', 'in', self.sale_order_id.ids)]
                domain += [('state', '=', 'done')]
                domain += [('id', '!=', self.id)]
                txs = self.env['payment.transaction'].sudo().search(
                    domain)
                print("txns ===>>>> " + str(txs))
                txn_gift_amt = 0
                for txn in txs:
                    if txn.gift_lines:
                        for gift_line in txn.gift_lines:
                            txn_gift_amt += float(
                                gift_line.transaction_amount)
                    if txn.amount != txn_gift_amt:
                        txn.write({'amount': txn_gift_amt})

                domain = [
                    ('sale_order_ids', '=', self.sale_order_id.id)]
                domain += [('state', '=', 'done')]
                paid_txns = self.env['payment.transaction'].sudo().search(
                    domain)
                paid_txns_amt = 0
                if len(paid_txns) > 1:
                    for paid_txn in paid_txns:
                        paid_txns_amt += paid_txn.amount

                if paid_txns_amt == self.sale_order_id.amount_total:
                    self.write({'state': 'done'})
                    sale_lock = get_sale_lock(self.env)
                    if self.sale_order_id.state not in ['done', 'lock']:
                        if self.sale_order_id.amount_total == self.amount:
                            self.sale_order_id.action_confirm()
                    if sale_lock:
                        if self.sale_order_id.amount_total == self.amount:
                            self.sale_order_id.action_done()

        return response

    def _monerischt_card_convert(self, move_id, data, transaction):
        transaction = {}
        transaction['provider_reference'] = data.get('ReferenceNum')
        transaction['amount'] = data.get('TransAmount')
        # transaction['date'] = data.get('date') if data.get(
        #     'date') != False or 'null' else False
        # if data.get('date_stamp') and data.get('date_stamp') != 'null' and data.get('time_stamp') and data.get('time_stamp') != 'null':
        #     dateTime = data.get('date_stamp') + ' ' + data.get('time_stamp')
        #     transaction['date'] = data.get(dateTime, fields.datetime.now())
        transaction['partner_country_id'] = self.partner_id.country_id.id
        transaction['state'] = data.get('state')
        transaction['state_message'] = data.get('Message').replace(
            "\n", "") if data.get('Message') and data.get('Message') != 'null' else ''
        # transaction['type'] = "validation"
        # Moneris Details
        transaction['moneris_card_name'] = data.get('CardType') or ''
        transaction['moneris_customer_id'] = data.get('ResolveData').get(
            'cust_id') if data.get('ResolveData') else ''
        transaction['moneris_receipt_id'] = data.get('ReceiptId') or ''
        transaction['moneris_response_code'] = data.get('ResponseCode') or ''
        transaction['moneris_credit_card'] = data.get('ResolveData').get(
            'masked_pan') if data.get('ResolveData') else ''
        transaction['moneris_expiry_date'] = data.get('ResolveData').get(
            'expdate') if data.get('ResolveData') else ''
        transaction['moneris_transaction_time'] = data.get('TransTime') or ''
        transaction['moneris_transaction_date'] = data.get('TransDate') or ''
        transaction['moneris_transaction_id'] = data.get('TransID') or ''
        transaction['moneris_payment_type'] = data.get('PaymentType') or ''
        transaction['moneris_reference_no'] = data.get('ReferenceNum') or ''
        transaction['moneris_txn_type'] = data.get('TransType') or ''
        transaction['moneris_bank_approval'] = data.get('AuthCode') or ''
        transaction['moneris_card_holder'] = data.get('ResolveData').get(
            'cust_id') if data.get('ResolveData') else ''
        transaction['moneris_order_id'] = data.get(
            'ReceiptId') or data.get('gift_card').get('order_no') if data.get('gift_card') else '' or ''
        transaction['moneris_iso_code'] = data.get('ISO') or ''
        transaction['moneris_transaction_key'] = ''
        transaction['moneris_transaction_no'] = data.get('TransID') or ''
        transaction['moneris_card_amount'] = data.get('TransAmount') or ''
        transaction['moneris_card_type'] = 'card'
        return transaction

    def _moneris_fraud_process(self, data):
        try:
            if data.get('response', {}).get('receipt').get('cc', {}).get('fraud', {}):
                fraud = data.get('response', {}).get(
                    'receipt').get('cc', {}).get('fraud', {})
                fraud_lines = []
                if fraud.get('avs') and self.provider_id.moneris_avs:
                    fraud_line = {}
                    fraud_line['transaction_type'] = 'avs'
                    fraud_line['decision_origin'] = fraud.get(
                        'avs').get('decision_origin')
                    fraud_line['result'] = fraud.get('avs').get('result')
                    fraud_line['condition'] = fraud.get('avs').get('condition')
                    fraud_line['status'] = fraud.get('avs').get('status')
                    fraud_line['code'] = fraud.get('avs').get('code')
                    fraud_line['details'] = fraud.get('avs').get('details')
                    fraud_line['transaction_id'] = self.id
                    fraud_lines.append(fraud_line)

                if fraud.get('cvd') and self.provider_id.moneris_cvv:
                    fraud_line = {}
                    fraud_line['transaction_type'] = 'cvd'
                    fraud_line['decision_origin'] = fraud.get(
                        'cvd').get('decision_origin')
                    fraud_line['result'] = fraud.get('cvd').get('result')
                    fraud_line['condition'] = fraud.get('cvd').get('condition')
                    fraud_line['status'] = fraud.get('cvd').get('status')
                    fraud_line['code'] = fraud.get('cvd').get('code')
                    fraud_line['details'] = fraud.get('cvd').get('details')
                    fraud_line['transaction_id'] = self.id
                    fraud_lines.append(fraud_line)

                if fraud.get('3d_secure') and self.provider_id.moneris_3d_secure:
                    fraud_line = {}
                    fraud_line['transaction_type'] = '3d_secure'
                    fraud_line['decision_origin'] = fraud.get(
                        '3d_secure').get('decision_origin')
                    fraud_line['result'] = fraud.get('3d_secure').get('result')
                    fraud_line['condition'] = fraud.get(
                        '3d_secure').get('condition')
                    fraud_line['status'] = fraud.get('3d_secure').get('status')
                    fraud_line['code'] = fraud.get('3d_secure').get('code')
                    fraud_line['details'] = fraud.get(
                        '3d_secure').get('details')
                    fraud_line['details_veres'] = fraud.get(
                        '3d_secure').get('VERes')
                    fraud_line['details_pares'] = fraud.get(
                        '3d_secure').get('PARes')
                    fraud_line['details_message'] = fraud.get(
                        '3d_secure').get('message')
                    fraud_line['details_cavv'] = fraud.get(
                        '3d_secure').get('cavv')
                    fraud_line['details_loadvbv'] = fraud.get(
                        '3d_secure').get('loadvbv')
                    fraud_line['transaction_id'] = self.id
                    fraud_lines.append(fraud_line)

                if fraud.get('kount') and self.provider_id.moneris_kount:
                    fraud_line = {}
                    fraud_line['transaction_type'] = 'kount'
                    fraud_line['decision_origin'] = fraud.get(
                        'kount').get('decision_origin')
                    fraud_line['result'] = fraud.get('kount').get('result')
                    fraud_line['condition'] = fraud.get(
                        'kount').get('condition')
                    fraud_line['status'] = fraud.get('kount').get('status')
                    fraud_line['code'] = fraud.get('kount').get('code')
                    fraud_line['details'] = fraud.get('kount').get('details')
                    fraud_line['transaction_id'] = self.id

                    fraud_line['details_responsecode'] = fraud.get(
                        'kount').get('responseCode')
                    fraud_line['details_receipt_id'] = fraud.get(
                        'kount').get('receiptID')
                    fraud_line['details_score'] = fraud.get(
                        'kount').get('score')
                    try:
                        error_msg = ""
                        if type(fraud.get('kount').get('error')) == list:
                            for error in fraud.get('kount').get('error'):
                                error_msg += error if error_msg == "" else "\n" + error_msg
                            fraud_line['details_error'] = error_msg
                        if type(fraud.get('kount').get('error')) == str:
                            fraud_line['details_error'] = fraud.get(
                                'kount').get('error')
                    except Exception as e:
                        _logger.warning('Exception: %s' % (e.args))
                    fraud_line['transaction_id'] = self.id
                    fraud_lines.append(fraud_line)
                if len(fraud_lines) > 0:
                    self.env['moneris.fraud.lines'].sudo().create(fraud_lines)

        except Exception as e:
            _logger.warning("Error: %s" % (e.args))

    def _mc_process_session(self, session, gift_total, order_id):
        if session.get('tx_kwargs', {}):
            kwargs = session.get('tx_kwargs', {})
            for key, value in kwargs.items():
                if value.get('s2s_do_transaction'):
                    response = value.get(
                        's2s_do_transaction', {}).get('response', {})
                    receipt = response.get('receipt', {})
                    cc = response.get('cc', {})
                    cc_amount = 0
                    if cc.get('amount'):
                        cc_amount = float(cc['amount'])
                        if float(cc['amount']) == 0:
                            print("""Payment with only Credit Card""")
                        elif float(cc['amount']) > 0:
                            print("""Payment with both Credit Card and Card""")
                    _logger.info("Number of gift lines ===>>>" +
                                 str(len(receipt.get('gift', []))))

                    if receipt.get('gift'):
                        for gift in receipt.get('gift', []):
                            gift_total += float(gift['transaction_amount'])
                            if gift.get('order_no'):
                                order_name = gift.get(
                                    'order_no').split("/")[0]
                                if order_name in self.reference:
                                    print("""Order Matches""")
                                    gift_id = self.env['transaction.gift.lines'].create(
                                        gift)
                                    gift_id.update({'gift_id': self.id})

                    if cc_amount > 0 and gift_total == 0:
                        self.write({
                            'moneris_card_type': 'card',
                        })

                    if cc_amount > 0 and gift_total > 0:
                        self.write({
                            'moneris_card_type': 'Card with Gift',
                        })

                    if cc_amount > 0 and gift_total < self.amount:
                        print("""Payment by both Card and Gift Card""")
                        # Find transactions based on Transaction Number
                        # If total Amount same as Gift Amount
                        domain = [('state', '=', 'done')]
                        domain += [('amount', '=', 0.00)]
                        domain += [('sale_order_id', 'in', order_id.ids)]
                        txns = self.env['payment.transaction'].sudo().search(
                            domain, limit=1)
                        if txns:
                            txn_gift_total = 0
                            reference = ''
                            if txns.gift_lines:
                                for gift_line in txns.gift_lines:
                                    txn_gift_total += float(
                                        gift_line.transaction_amount)
                                    reference += gift_line.reference_no if reference == '' else ',' + gift_line.reference_no

                            if txn_gift_total != txns.amount:
                                txns.write({
                                    'amount': txn_gift_total
                                })

                    if cc_amount == 0 and gift_total == self.amount:
                        self.write({
                            'moneris_card_type': 'gift',
                            'state': 'done',
                            # 'type': 'validation',
                            'date_validate': fields.Datetime.now(),
                        })
                        if len(receipt.get('gift', [])) == 1:
                            self.write({
                                'moneris_rem_balance': receipt.get('gift', [])[0].get('balance_remaining', ''),
                                'moneris_gift_txntype': '',
                                'moneris_gift_cardnum': receipt.get('gift', [])[0].get('first6last4', ''),
                                'moneris_gift_orderno': receipt.get('gift', [])[0].get('order_no', ''),
                                'moneris_gift_refnum': receipt.get('gift', [])[0].get('reference_no', ''),
                                'moneris_gift_charge': receipt.get('gift', [])[0].get('transaction_amount', ''),
                                'moneris_gift_txnnum': receipt.get('gift', [])[0].get('transaction_no', ''),
                            })

                        # Find transactions based on Transaction Number
                        # If total Amount same as Gift Amount
                        domain = [('state', '=', 'done')]
                        domain += [('amount', '=', 0.00)]
                        domain += [('sale_order_id', 'in', order_id.ids)]
                        txns = self.env['payment.transaction'].sudo().search(
                            domain, limit=1)
                        if txns:
                            txns.write({'state': 'draft'})
                            txns.unlink()
                        return receipt

    # def _monerischeckout_create_transaction_request(self, opaque_data):
    #     """ Create an Authorize.Net payment transaction request.

    #     Note: self.ensure_one()

    #     :param dict opaque_data: The payment details obfuscated by Authorize.Net
    #     :return:
    #     """
    #     self.ensure_one()

    #     authorize_API = AuthorizeAPI(self.provider_id)
    #     if self.provider_id.capture_manually or self.operation == 'validation':
    #         return authorize_API.authorize(self, opaque_data=opaque_data)
    #     else:
    #         return authorize_API.auth_and_capture(self, opaque_data=opaque_data)


class PaymentToken(models.Model):
    _inherit = 'payment.token'

    moneris_profile = fields.Char(
        string='Moneris Profile ID', help="Datakey in the Moneris Vault.")
    moneris_ticket = fields.Char(string='Moneris Ticket No')
    moneris_verified = fields.Boolean(string='Moneris Verified', )
    provider = fields.Selection(
        string='Provider', related='provider_id.code', readonly=False)
    # change
    save_token = fields.Boolean(
        string='Save Cards', related='provider_id.allow_tokenization', readonly=False)
    moneris_recurring = fields.Boolean(
        string='Recurring Payment',
        help='Enable this token for automated recurring invoice payments.',
    )

    # def unlink(self):
    #     if self.provider_id.code == 'monerischeckout':
    #         if not self.provider_id.allow_token_delete:
    #             print("user_partner_id===>>>" +
    #                   str(self.env.user.partner_id.id))
    #             print("partner_id===>>>" + str(self.partner_id.id))
    #             if self.env.user.partner_id.id != self.partner_id.id:
    #                 raise UserError(
    #                     _("You have no permission to delete this record. Only `%s` can delete his/her record." % (
    #                         self.partner_id.name)))
    #
    #     result = super(PaymentToken, self).unlink()
    #
    #     return result


class TransactionGiftLines(models.Model):
    _name = 'transaction.gift.lines'
    _description = 'Transaction Gift Lines'

    balance_remaining = fields.Char("Balance Remaining")
    first6last4 = fields.Char("f6l4")
    order_no = fields.Char("Order No.")
    reference_no = fields.Char("Refrence No")
    response_code = fields.Char("Response Code")
    transaction_amount = fields.Char("Transaction Amount")
    transaction_no = fields.Char("Transaction No.")
    gift_id = fields.Many2one('payment.transaction', string='Gift Id')


class MonerisFraudLines(models.Model):
    _name = 'moneris.fraud.lines'
    _description = 'Moneris Fraud Lines'

    transaction_type = fields.Selection(selection=FRAUD_TYPES, required=True)
    decision_origin = fields.Char("Decision Origin")
    result = fields.Char("Result")
    condition = fields.Char("Condition")
    status = fields.Char("Status")
    code = fields.Char("Code")
    details = fields.Char("Details")
    # 3d_secure
    details_veres = fields.Char("VERes")
    details_pares = fields.Char("PARes")
    details_message = fields.Char("Message")
    details_cavv = fields.Char("CAVV")
    details_loadvbv = fields.Char("loadvbv")
    # Kount
    details_responsecode = fields.Char("Response Code")
    details_receipt_id = fields.Char("Receipt ID")
    details_score = fields.Char("Kount Score")
    details_error = fields.Char("Error")
    transaction_id = fields.Many2one(
        'payment.transaction', string='Transaction Id')

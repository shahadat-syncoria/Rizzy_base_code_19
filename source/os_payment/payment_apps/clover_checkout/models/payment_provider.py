from odoo import _, api, fields, models

from werkzeug.urls import url_encode, url_join, url_parse

import logging
import requests

from odoo.exceptions import ValidationError, UserError
from odoo.addons.odoosync_base.utils.app_payment import AppPayment
import json

_logger = logging.getLogger(__name__)

class PaymentProviderClover(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('clover_checkout', "Clover Checkout")], ondelete={'clover_checkout': 'set default'})


    clover_public_api_key = fields.Char(string="Public API key", groups='base.group_system')
    # clover_token = fields.Char(string="Token", required_if_provider='clover_checkout', groups='base.group_system')
    # clover_merchant_id = fields.Char(string="Merchant Id", required_if_provider='clover_checkout', groups='base.group_system')



    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'clover_checkout').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    def _clover_checkout_make_request(self, endpoint, payload=None, method=None):
        self.ensure_one()

        try:
            srm = AppPayment(service_name='clover_checkout', service_type=endpoint, service_key=self.token)
            srm.data = payload
            response = srm.payment_process(company_id=self.company_id.id, omnisync_id=self.account_id)
            # if response.get('error') or 'errors_message' in response:
            #     error = response.get('error') if 'error' in response else response.get("errors_message")
            #     raise UserError(_(error))

            # #dummy data
            # response = {
            #       "id": "ABDFEFG1HIJK2",
            #       "amount": 122,
            #       "payment_method_details": "card",
            #       "amount_refunded": 0,
            #       "currency": "usd",
            #       "created": 123456789123,
            #       "captured": 'true',
            #       "ref_num": 987654321,
            #       "auth_code": 123456,
            #       "outcome": {
            #         "network_status": "approved_by_network",
            #         "type": "authorized"
            #       },
            #       "paid": 'true',
            #       "status": "succeeded",
            #       "source": {
            #         "id": "clv_1AAAAAAbCdefJK2l3MnoPQ4r",
            #         "brand": "DISCOVER",
            #         "exp_month": 12,
            #         "exp_year": 2025,
            #         "first6": 112233,
            #         "last4": 1111
            #       },
            #       "ecomind": "ecom"
            #     }

        except requests.exceptions.ConnectionError as e:
            _logger.exception("unable to reach endpoint at %s", e)
            raise ValidationError("Clover Checkout: " + _("Could not establish the connection to the API."))
        return response
        # return response

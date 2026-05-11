# -*- coding: utf-8 -*-
# © Syncoria Inc.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

# Module: payment_globalpay
# This module contains functionality for interacting with the GlobalPay API,

import hashlib
import hmac
import logging
import pprint
import requests
import six
from werkzeug.urls import url_join
from odoo import  api, fields, models
from odoo.exceptions import ValidationError,UserError
import base64
import json
from datetime import datetime
from odoo.addons.odoosync_base.utils.app_payment import AppPayment


_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('globalpay', "GlobalPay")], ondelete={'globalpay': 'set default'})
    # globalpay_access_token = fields.Char(string="access Token", help="The key solely used to identify the account with GlobalPay",required_if_provider='globalpay')
    # globalpay_user_password = fields.Char(string="API Password", required_if_provider='globalpay', groups='base.group_system')
    # globalpay_api_version = fields.Char(string="API Version", required_if_provider='globalpay', groups='base.group_system')
    # globalpay_app_id = fields.Char(string="App ID", required_if_provider='globalpay', groups='base.group_system')
    # globalpay_app_key = fields.Char(string="App Key", required_if_provider='globalpay', groups='base.group_system')

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'globalpay').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_refund': 'partial',
            'support_tokenization': True,
        })

    def _globalpay_get_api_url(self):
        if self.state == 'enabled':
            return 'https://apis.globalpay.com'
        else:  # test environment
            return 'https://apis.sandbox.globalpay.com'
    
    @api.model
    def get_globalpay_access_token(self, permissions=None):
        """
        Get GlobalPay Access Token.

        :param permissions: Permissions to include in the request.
                            If not provided or equals 'single', defaults to ['PMT_POST_Create_Single'].
        :return: Bearer Access Token or None in case of failure.
        """
        # GlobalPay credentials
        # app_id = self.globalpay_app_id
        # app_key = self.globalpay_app_key
        # nonce = self.generate_dynamic_nonce()

        # Auth API endpoint URL
        auth_api_url = url_join(self._globalpay_get_api_url(), "/ucp/accesstoken")

        # Request headers
        headers = {
            'content-type': 'application/json',
            'x-gp-version': self.globalpay_api_version
        }

        # Request body
        data = {
            "app_id": app_id,
            "nonce": nonce,
            "secret": self.encode_secret_sha(nonce, app_key),
            "grant_type": "client_credentials",
            "interval_to_expire": "10_MINUTES"
        }

        # Conditionally add permissions if provided and not equal to "single"
        if permissions and permissions.lower() == "single":
            data["permissions"] = ["PMT_POST_Create_Single"]

        _logger.info("Requesting GlobalPay access token...")
        _logger.info("auth_api_url %s json.dumps(data) %s and headers %s",auth_api_url, json.dumps(data),headers )
        _logger.info("json.dumps(data) %s", json.dumps(data))

        # Make the POST request to generate the Bearer Access Token
        response = requests.post(auth_api_url, headers=headers, data=json.dumps(data))

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            auth_data = response.json()

            # Extract the Bearer Access Token
            access_token = auth_data.get("token")

            _logger.info("GlobalPay access token retrieved successfully. %s", auth_data)

            return access_token
        else:
            _logger.error("Failed to retrieve GlobalPay access token. Status code: %s", response.status_code)
            _logger.error("Response content: %s", response.text)

            # Handle the error or return None in case of failure
            return None
            
    def generate_dynamic_nonce(self):
        """
        Generate a dynamic nonce based on the current timestamp.

        :return: Dynamic nonce string.
        """
        date = datetime.utcnow()
        nonce_date = date.isoformat()
        return nonce_date

    def encode_secret_sha(self, nonce, app_key):
        """
        Encode the secret using SHA format, incorporating app_id and nonce.

        :param app_id: GlobalPay application ID.
        :param nonce: Dynamic nonce.
        :return: SHA-encoded secret.
        """
        s512_txt = nonce + app_key
        secret = hashlib.sha512(s512_txt.encode('utf-8')).hexdigest()
        return secret
    
    def _globalpay_make_request(self, endpoint, payload=None, method='POST', token=None):
        """ Make a request to globalpay API at the specified endpoint.

        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :param str token: The access token to be used for authorization.
        :return: The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()

        self.ensure_one()
        try:
            srm = AppPayment(service_name='global_payment', service_type=endpoint, service_key=self.token)
            srm.data = payload
            response = srm.payment_process(company_id=self.company_id.id)
            if response.get('error') or 'errors_message' in response:
                error = response.get('error') if 'error' in response else response.get("errors_message")
                raise UserError((error))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", )
            raise ValidationError(
                "GlobalPay: " + ("Could not establish the connection to the API.")
            )
        except Exception as e:
            # _logger.exception("Unable to reach endpoint at %s", )
            raise ValidationError(
                "GlobalPay: " + (str(e))
            )
        return response


    def _should_build_inline_form(self, is_validation=False):
        """ Return whether the inline payment form should be instantiated.

        For a provider to handle both direct payments and payments with redirection, it must
        override this method and return whether the inline payment form should be instantiated (i.e.
        if the payment should be direct) based on the operation (online payment or validation).

        :param bool is_validation: Whether the operation is a validation.
        :return: Whether the inline form should be instantiated.
        :rtype: bool
        """
        return True

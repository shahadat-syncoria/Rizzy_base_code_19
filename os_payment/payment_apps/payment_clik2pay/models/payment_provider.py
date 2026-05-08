import hashlib
import hmac
import logging
import pprint
import requests
import six
from werkzeug.urls import url_join
from odoo import  api, fields, models
from odoo.exceptions import ValidationError
import base64
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('clik2pay', "Clik2Pay")], ondelete={'clik2pay': 'set default'})
    # clik2pay_user_name = fields.Char(
    #     string="API User Name", help="The key solely used to identify the account with Clik2pay",
    #     required_if_provider='clik2pay')
    # clik2pay_user_password = fields.Char(
    #     string="API Password", required_if_provider='clik2pay', groups='base.group_system')
    # clik2pay_api_key = fields.Char(
    #     string="API Key", required_if_provider='clik2pay', groups='base.group_system')
    clik2pay_tampered_payment = fields.Boolean('Accept Tampered Payment', default=True)

    #=== COMPUTE METHODS ===#

    def _compute_feature_support_fields(self):
        """ Override of `payment` to enable additional features. """
        super()._compute_feature_support_fields()
        self.filtered(lambda p: p.code == 'clik2pay').update({
            'support_express_checkout': False,
            'support_manual_capture': False,
            'support_refund': 'partial',
            'support_tokenization': False,
        })

    def _clik2pay_get_api_url(self):
        if self.state == 'enabled':
            return 'https://api.clik2pay.com/open/v1/'
        else:  # test environment
            return 'https://api.sandbox.clik2pay.com/open/v1/'

    def _clik2pay_get_token_url(self):
        if self.state == 'enabled':
            return 'https://api-auth.clik2pay.com/oauth2/token'
        else:  # test environment
            return 'https://api-auth.sandbox.clik2pay.com/oauth2/token'
    
    # @api.model
    # def get_clik2pay_access_token(self):
    #     # Clik2pay credentials
    #     username = self.clik2pay_user_name
    #     password = self.clik2pay_user_password
    #
    #     # Base64 encode your username and password
    #     auth_credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
    #
    #     # Auth API endpoint URL
    #     auth_api_url = self._clik2pay_get_token_url()
    #
    #     # Request headers
    #     headers = {
    #         "Authorization": f"Basic {auth_credentials}",
    #         "Content-Type": "application/x-www-form-urlencoded"
    #     }
    #
    #     # Request body
    #     data = {
    #         "grant_type": "client_credentials",
    #         "scope": "payment_request/all"
    #     }
    #
    #     _logger.info("Requesting Clik2pay access token...")
    #
    #     # Make the POST request to generate the Bearer Access Token
    #     response = requests.post(auth_api_url, headers=headers, data=data)
    #
    #     # Check if the request was successful
    #     if response.status_code == 200:
    #         # Parse the JSON response
    #         auth_data = response.json()
    #
    #         # Extract the Bearer Access Token
    #         access_token = auth_data.get("access_token")
    #
    #         _logger.info("Clik2pay access token retrieved successfully.")
    #
    #         return access_token
    #     else:
    #         _logger.error("Failed to retrieve Clik2pay access token. Status code: %s", response.status_code)
    #         _logger.error("Response content: %s", response.text)
    #
    #         # Handle the error or return None in case of failure
    #         return None
    
    def _clik2pay_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to clik2pay API at the specified endpoint.


        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        try:
            srm = AppPayment(service_name='clik2pay', service_type=endpoint, service_key=self.token)
            srm.data = payload
            response = srm.payment_process(company_id=self.company_id.id)
            if response.get('error') or 'errors_message'  in response:
                error = response.get('error') if 'error' in response else response.get("errors_message")
                raise ValidationError((error))
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", )
            raise ValidationError(
                "Clik2Pay: " + ("Could not establish the connection to the API.")
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

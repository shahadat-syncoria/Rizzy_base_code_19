# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from os import access

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.orm.utils import SUPERUSER_ID

import logging

_logger = logging.getLogger(__name__)

STATECODE_REQUIRED_COUNTRIES = ["US", "CA", "PR ", "IN"]


class AppPayment:
    def __init__(self, service_name, service_type, service_key):
        self.service_name = service_name
        self.service_type = service_type
        self.service_key = service_key
        self.data = {}

    def _get_omnisync_account(self):
        env = request.env(user=SUPERUSER_ID)
        if self.service_name in ['moneris_cloud', 'moneris_cloud_go', 'clover_cloud']:
            journal = env['account.journal'].search([('token', '=', self.service_key)], limit=1)
            if journal:
                return journal.account_id

        provider = env['payment.provider'].search([('token', '=', self.service_key)], limit=1)
        return provider.account_id if provider else False

    def payment_process(self,**kwargs):
        """[summary]"""

        formatted_response = {"url": []}

        url = "/api/v1/services/payment_gateway/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key,
        }
        data = self.__dict__

        omnisync_id = kwargs.get('omnisync_id') or self._get_omnisync_account()

        try:
            formatted_response = request.env(user=SUPERUSER_ID)["omnisync.connector"].omnisync_api_call(
                headers=headers,
                url=url,
                request_type=request_type,
                data=data,
                company_id=kwargs['company_id'],
                omnisync_id=omnisync_id
                # debug_logging=debug_logging,
                # access_token=access_token
            )

            _logger.info("formatted_response ====>>>>", formatted_response)
            if formatted_response.get("errors"):
                formatted_response['error'] = formatted_response.get("errors")
            elif formatted_response.get("error"):
                formatted_response['error'] = formatted_response.get("error")
            elif 'error' not in formatted_response:
                formatted_response['error'] = None

            return formatted_response

        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

    def resolvepay_api_call(self, **kwargs):
        formatted_response = {"url": []}

        url = "/api/v1/services/payment_gateway/"
        request_type = "POST"
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key,
        }
        data = self.__dict__
        omnisync_id = self._get_omnisync_account()

        try:
            formatted_response = request.env(user=SUPERUSER_ID)["omnisync.connector"].omnisync_api_call(
                headers=headers,
                url=url,
                request_type=request_type,
                data=data,
                company_id=kwargs['company_id'],
                omnisync_id=omnisync_id
            )

            _logger.info("formatted_response ====>>>> %s", formatted_response)

            return formatted_response

        except Exception as e:
            formatted_response['errors_message'] = e.args[0]
        return formatted_response

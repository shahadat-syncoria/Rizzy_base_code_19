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

import logging

_logger = logging.getLogger(__name__)


class AppMarketplace:
    def __init__(self, service_name, service_key):
        self.service_name = service_name
        self.service_key = service_key
        self.data = {}

    def marketplace_process(self,**kwargs):
        """[summary]"""

        formatted_response = {"url": []}

        url = "/api/v1/services/marketplace/api_call/"
        request_type = 'POST'
        headers = {
            "Content-Type": "application/json",
            "X-Service-Key": self.service_key,
        }
        data = self.__dict__
        env = kwargs.get('env')
        omnisync_id = False
        marketplace_id = env['marketplace.instance'].search([('token','=',self.service_key)])
        if marketplace_id:
            omnisync_id = marketplace_id[0].account_id
        try:
            formatted_response = env["omnisync.connector"].omnisync_api_call(
                headers=headers,
                url=url,
                request_type=request_type,
                data=data,
                company_id=kwargs['company_id'],
                debug_logging=True,
                omnisync_id=omnisync_id,
            )

            _logger.info("formatted_response ====>>>> %s" % formatted_response)

            return formatted_response

        except Exception as e:
            formatted_response['error'] = e.args[0]
        return formatted_response

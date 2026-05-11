# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


import logging
import json
from odoo import models, fields, api, exceptions, _
from ast import literal_eval
from pprint import pprint
logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:
    logger.info("Unable to import requests, please install it with pip install requests")


class OmnisyncConnector(models.Model):
    _name = 'omnisync.connector'
    _description = 'Omnisync Connector'

    def omnisync_api_call(self, **kwargs):
        """
        We will be running the api calls from here
        :param kwargs: dictionary with all the necessary parameters,
        such as url, header, data,request type, etc
        :return: response obtained for the api call
        """
        if not kwargs:
            # no arguments passed
            return
        if kwargs.get('omnisync_id'):
            omni_account_id = kwargs.get('omnisync_id')
        else:
            OmniAccount = self.env['omni.account'].sudo()
            omni_account_id = OmniAccount.search([('state','=','active'),('company_id','=',kwargs.get('company_id'))], limit=1)
        # fetching access token from settings
        try:
            access_token = omni_account_id.token or kwargs.get('access_token')
        except:
            access_token = False
            pass
        # fetching host name
        try:
            server_url = omni_account_id.server_url
        except:
            server_url = False
            pass
        if not access_token or not server_url:
            raise exceptions.AccessDenied(_('Please check the OmniSync Account configurations!'))
        if omni_account_id.state != 'active':
            raise exceptions.AccessDenied(_('OmniSync Account is not active!'))

        request_type = kwargs.get('request_type') or 'GET'
        complete_url = server_url + kwargs.get('url')
        logger.info("%s", complete_url)
        headers = kwargs.get('headers')
        headers['Authorization'] = 'Token ' + access_token
        # data = json.dumps(kwargs.get('data')) if kwargs.get('data') else None
        data = kwargs.get('data') if kwargs.get('data') else {}
        if data.get("service_key"):
            del(data["service_key"])
        res = False

        if kwargs.get('debug_logging'):
            logger.info("request_type ===>>> %s", request_type)
            logger.info("complete_url ===>>> %s", complete_url)
            logger.info("headers ===>>> %s", headers)
            logger.info("data ===>>> %s", print(data))

        try:
            res= requests.request(method=request_type,url=complete_url, headers=headers, json=data)
            if kwargs.get('debug_logging'):
                logger.info("res ===>>> %s", res)
                logger.info("res.text ===>>> %s", res.text)
            items = json.loads(res.text)
            if res.status_code == 403:
                items["errors"] = items.get("detail")
            return items
        except Exception as e:
            # if 'Allowed memory size' in res.text:
            #     logger.info(str(res.text))
            #     raise exceptions.UserError(_(res.text))
            logger.info("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured  %s") %e)
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging
import json
from odoo import models, fields, api, exceptions, _
_logger = logging.getLogger(__name__)
import requests

class ShopifyConnect(models.Model):
    _inherit = 'marketplace.connector'

    def _assert_omnisync_subscription_active(self, marketplace_instance):
        # Omnisync subscription check removed — authorization is handled
        # entirely by the Shopify OAuth token on the instance.
        pass

    def _build_shopify_payload(self, kwargs, req_type):
        return {
            "type": req_type,
            "shopify_endpoint": kwargs.get('url'),
            "payload": kwargs.get('data', {}),
            "params": kwargs.get('params', {}),
            "is_raw_endpoint": kwargs.get('is_raw_endpoint', False),
        }

    def shopify_api_call(self, **kwargs):
        """
        We will be running the api calls from here
        :param kwargs: dictionary with all the necessary parameters,
        such as url, header, data,request type, etc
        :return: response obtained for the api call
        """
        if kwargs.get('kwargs'):
            kwargs = kwargs.get('kwargs')
        if not kwargs:
            # no arguments passed
            return

        req_type = kwargs.get('type') or 'GET'
        complete_url = kwargs.get('url')
        headers = kwargs.get('headers')

        """
        {
            "service_name":"shopify",
            "data":{
                "type": "GET",
                "shopify_endpoint": "/admin/oauth/access_scopes.json",
                "payload":{},
                "params":{
                    "limit":250
                }
            }
        }
        """
        
        payload = self._build_shopify_payload({
            **kwargs,
            "url": complete_url,
        }, req_type)
        marketplace_instance = kwargs.get('marketplace_instance_id')
        if marketplace_instance:
            self._assert_omnisync_subscription_active(marketplace_instance)
            return self._shopify_direct_rest_call(marketplace_instance, payload)
        raise exceptions.UserError(_("Legacy Omnisync Shopify proxy mode is removed. Use Direct OAuth mode."))

    def shopify_graphql_call(self, **kwargs):
        """
        GraphQL transport wrapper that keeps connector return format stable.
        """
        if kwargs.get('kwargs'):
            kwargs = kwargs.get('kwargs')
        if not kwargs:
            return

        headers = kwargs.get('headers') or {}
        query = kwargs.get('query')
        if not query:
            raise exceptions.UserError(_("GraphQL query is required."))

        payload_data = {
            "query": query,
            "variables": kwargs.get('variables') or {},
        }
        if kwargs.get('operation_name'):
            payload_data["operationName"] = kwargs.get('operation_name')

        payload = {
            "type": "POST",
            "shopify_endpoint": kwargs.get('url') or "/graphql.json",
            "payload": payload_data,
            "params": kwargs.get('params', {}),
            "is_raw_endpoint": kwargs.get('is_raw_endpoint', False),
        }
        marketplace_instance = kwargs.get('marketplace_instance_id')
        if marketplace_instance:
            self._assert_omnisync_subscription_active(marketplace_instance)
            return self._shopify_direct_graphql_call(marketplace_instance, payload)
        raise exceptions.UserError(_("Legacy Omnisync Shopify proxy mode is removed. Use Direct OAuth mode."))

    def _build_direct_shopify_url(self, marketplace_instance, endpoint, is_raw=False):
        host = (marketplace_instance.marketplace_host or '').replace('https://', '').replace('http://', '').strip().rstrip('/')
        base = "https://%s" % host
        if is_raw:
            return "%s%s" % (base, endpoint)
        return "%s/admin/api/%s%s" % (base, marketplace_instance.marketplace_api_version, endpoint)

    def _shopify_direct_rest_call(self, marketplace_instance, payload):
        if not marketplace_instance.shopify_oauth_token:
            raise exceptions.UserError(_("Missing Shopify OAuth token. Authorize this instance first."))
        url = self._build_direct_shopify_url(
            marketplace_instance,
            payload.get('shopify_endpoint') or '',
            payload.get('is_raw_endpoint', False),
        )
        headers = {
            'X-Shopify-Access-Token': marketplace_instance.shopify_oauth_token,
            'Content-Type': 'application/json',
        }
        res = requests.request(
            payload.get('type') or 'GET',
            url,
            headers=headers,
            data=json.dumps(payload.get('payload')) if payload.get('payload') else None,
            params=payload.get('params') or {},
            timeout=30,
        )
        try:
            body = res.json() if res.text else {}
        except Exception:
            body = {'errors': res.text or _('Shopify request failed')}
        if res.status_code >= 400:
            if not body.get('errors'):
                body['errors'] = res.text
        body['links'] = res.links if hasattr(res, 'links') else None
        return body, body.get('links')

    def _shopify_direct_graphql_call(self, marketplace_instance, payload):
        if not marketplace_instance.shopify_oauth_token:
            raise exceptions.UserError(_("Missing Shopify OAuth token. Authorize this instance first."))
        url = self._build_direct_shopify_url(
            marketplace_instance,
            payload.get('shopify_endpoint') or '/graphql.json',
            payload.get('is_raw_endpoint', False),
        )
        headers = {
            'X-Shopify-Access-Token': marketplace_instance.shopify_oauth_token,
            'Content-Type': 'application/json',
        }
        res = requests.post(url, headers=headers, data=json.dumps(payload.get('payload') or {}), timeout=30)
        try:
            body = res.json() if res.text else {}
        except Exception:
            body = {'errors': res.text or _('Shopify GraphQL request failed')}
        body['links'] = res.links if hasattr(res, 'links') else None
        return body, body.get('links')

import hashlib
import hmac

import requests

from odoo import http, _
from odoo.http import request
from werkzeug.utils import redirect


class ShopifyOAuthController(http.Controller):
    def _verify_hmac(self, params, secret):
        incoming_hmac = params.get('hmac', '')
        message_parts = []
        for key in sorted(params.keys()):
            if key in ('hmac', 'signature'):
                continue
            message_parts.append("%s=%s" % (key, params.get(key)))
        message = '&'.join(message_parts)
        digest = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(digest, incoming_hmac)

    @http.route('/shopify/oauth/callback', type='http', auth='public', methods=['GET'], csrf=False, website=False)
    def shopify_oauth_callback(self, **kwargs):
        code = kwargs.get('code')
        shop = kwargs.get('shop')
        state = kwargs.get('state')
        if not (code and shop and state):
            return request.not_found()

        instance = request.env['marketplace.instance'].sudo().search([
            ('shopify_oauth_state', '=', state),
            ('shopify_auth_mode', '=', 'direct_oauth')
        ], limit=1)
        if not instance.exists():
            return request.not_found()

        if not self._verify_hmac(kwargs, instance.marketplace_secret_key or ''):
            return request.not_found()

        host = (shop or '').replace('https://', '').replace('http://', '').strip().rstrip('/')
        token_url = "https://%s/admin/oauth/access_token" % host
        payload = {
            'client_id': instance.marketplace_api_key,
            'client_secret': instance.marketplace_secret_key,
            'code': code,
        }
        res = requests.post(token_url, json=payload, timeout=20)
        data = res.json() if res.text else {}
        access_token = data.get('access_token')
        if not access_token:
            instance.message_post(body=_("Shopify OAuth failed: %s") % (res.text or res.status_code))
            # Must raise/return a real response, not an HTTPException object.
            return redirect('/web#id=%s&model=marketplace.instance&view_type=form' % instance.id)

        instance.write({
            'shopify_oauth_token': access_token,
            'marketplace_host': host,
            'shopify_oauth_state': False,
            'marketplace_state': 'confirm',
        })
        instance.message_post(body=_("Shopify OAuth connected successfully."))
        return redirect('/web#id=%s&model=marketplace.instance&view_type=form' % instance.id)


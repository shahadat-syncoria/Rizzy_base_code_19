# -*- coding: utf-8 -*-
###############################################################################
#    Harden omnisync_api_call for Shopify flows without changing odoosync_base.
###############################################################################

from odoo import models


class OmnisyncConnector(models.Model):
    _inherit = 'omnisync.connector'

    def omnisync_api_call(self, **kwargs):
        kwargs = dict(kwargs)
        if kwargs.get('headers') is None:
            kwargs['headers'] = {}
        if not isinstance(kwargs.get('data'), dict):
            kwargs['data'] = {}
        res = super().omnisync_api_call(**kwargs)
        return res if res is not None else {}

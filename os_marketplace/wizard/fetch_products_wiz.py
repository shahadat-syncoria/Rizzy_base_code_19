# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests
import logging
import base64
import re
from odoo import models, fields, exceptions, _

logger = logging.getLogger(__name__)


class ProductsFetchWizard(models.TransientModel):
    _name = 'products.fetch.wizard'
    _description = 'Product Fetch Wizard'
    _inherit = 'order.fetch.wizard'

    fetch_type = fields.Selection([
        ('to_odoo', 'Fetch data from Marketplace to Odoo'),
    ], default='to_odoo', string="Operation Type")

    def fetch_products(self):
        """Fetch products"""
        return self.fetch_products_to_odoo()

    def fetch_products_to_odoo(self):
        print("fetch_products_to_odoo")
        if self.instance_id:
            kwargs = {'marketplace_instance_id': self.instance_id}
            if self.shopify_product_id:
                kwargs['fetch_o_product'] = True
                kwargs['product_id'] = self.shopify_product_id
            if self.mappings_only:
                kwargs['mappings_only'] = True
            if hasattr(self, '%s_fetch_products_to_odoo' % self.instance_id.marketplace_instance_type):
                return getattr(self, '%s_fetch_products_to_odoo' % self.instance_id.marketplace_instance_type)(kwargs)

    def _cron_fetch_products(self):
        instance_id = self.env['marketplace.instance'].search([], limit=1)
        wizard_id = self.create({'instance_id': instance_id.id, 'date_from': fields.Date.today(), 'date_to': fields.Date.today()})
        wizard_id.fetch_products()
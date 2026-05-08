# -*- coding: utf-8 -*-


import random
import string
import re
from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    merchantAccountId = fields.Char(string="Merchant Account ID", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if val.get('merchantAccountId') is None:
                val['merchantAccountId'] = self._generate_merchant_account_id()
        return super(ResPartner, self).create(vals)

    def _generate_merchant_account_id(self):
        pattern = "^[a-zA-Z0-9]+$"
        minLength = 4
        maxLength = 50

        # Generate a random string based on pattern, minLength, and maxLength
        characters = string.ascii_letters + string.digits
        while True:
            merchant_account_id = ''.join(random.choice(characters) for _ in range(maxLength))
            if re.match(pattern, merchant_account_id) and minLength <= len(merchant_account_id) <= maxLength:
                return merchant_account_id

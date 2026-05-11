# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api


class ProductImage(models.Model):
    _inherit = 'product.image'

    shopify_id = fields.Char(string="Shopify Id", store=True, copy=False)


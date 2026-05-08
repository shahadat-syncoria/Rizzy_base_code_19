from random import randint

from odoo import fields, models


class ShopifyErrTag(models.Model):
    _name = 'shopify.err.tag'
    _description = "Shopify Error Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Error Name', required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)

    _name_uniq = models.Constraint(
        'unique (name)',
        'Error name already exists!',
    )

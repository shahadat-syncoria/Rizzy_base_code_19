from random import randint

from odoo import fields, models


class ShopifyCoupon(models.Model):
    _name = "shopify.coupon"
    _description = "Shopify Coupon"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Shopify Coupon Name', required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Shopify coupon name already exists !"),
    ]
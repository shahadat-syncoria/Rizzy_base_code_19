# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class CloverPaymentToken(models.Model):
    _inherit = 'payment.token'

    clover_checkout_id = fields.Char(help="The unique reference of the partner owning this token",
        readonly=True)
    clover_customer_id = fields.Char()

from odoo import api, fields, models, _


class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    shopify_carrier_name = fields.Char('Shopify Carrier Name')
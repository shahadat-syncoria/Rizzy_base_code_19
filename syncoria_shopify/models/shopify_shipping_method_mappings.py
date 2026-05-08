from odoo import api, fields, models


class ShopifyShippingMethodMappings(models.Model):
    _name = 'shopify.shipping.method.mappings'
    _description = 'Shopify Shipping Method Mappings'

    name = fields.Char('Shipping Method', required=True)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', required=True)
    product_id = fields.Many2one(related='carrier_id.product_id', string='Product')
    company_id = fields.Many2one(related='shopify_instance_id.company_id', string='Company')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True)

from odoo import api, fields, models


class ShopifyPaymentMethodMappings(models.Model):
    _name = 'shopify.payment.method.mappings'
    _description = 'Shopify Payment Method Mappings'

    name = fields.Char('Payment Gateway', required=True)
    journal_id = fields.Many2one('account.journal', 'Odoo Payment Journal', required=True)
    company_id = fields.Many2one(related='shopify_instance_id.company_id', string='Company')
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True)

class ShopifyRefundPaymentMethodMappings(models.Model):
    _name = 'shopify.refund.payment.method.mappings'
    _description = 'Shopify Refund Payment Method Mappings'

    name = fields.Char('Refund Payment Gateway', required=True)
    company_id = fields.Many2one(related='shopify_instance_id.company_id', string='Company')
    journal_id = fields.Many2one('account.journal', 'Odoo Refund Payment Journal', required=True,domain="[('company_id', '=',company_id)]")
    shopify_instance_id = fields.Many2one("marketplace.instance", string="Shopify Instance ID", required=True)

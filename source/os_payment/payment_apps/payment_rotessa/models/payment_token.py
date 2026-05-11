from odoo import fields,models,api

class RotessaPaymentToken(models.Model):
    _inherit = 'payment.token'


    rotessa_customer_id = fields.Char("Rotessa Customer ID")
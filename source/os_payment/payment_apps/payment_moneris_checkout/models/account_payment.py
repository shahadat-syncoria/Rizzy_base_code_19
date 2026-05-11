from odoo import fields,api,models

class AccountPayment(models.Model):
    _inherit = "account.payment"


    is_group_payment = fields.Boolean(default=False)
from odoo import fields, models, api


class Inherited(models.Model):
    _inherit = 'account.payment'

    is_clik2pay_sync_button_visible = fields.Boolean(compute='_check_is_clik2pay_sync_visible')

    @api.depends('payment_transaction_id')
    def _check_is_clik2pay_sync_visible(self):
        for rec in self:
            rec.is_clik2pay_sync_button_visible = rec.payment_transaction_id.provider_code == 'clik2pay' and rec.payment_transaction_id.refunds_count > 0


    def update_payment_refund_status(self):
        for rec in self:
            rec.payment_transaction_id.update_payment_refund_status()

from odoo import fields, models,api

class MonerisGoPosConfig(models.Model):
    _inherit = "pos.config"



    is_moneris_go_preauth_enabled = fields.Boolean('Is moneris Go Preauth Enabled',default=False)

    def _check_before_creating_new_session(self):
        for rec in self:
            is_enabled = any(rec.payment_method_ids.mapped('is_moneris_go_cloud'))
            if rec.is_moneris_go_preauth_enabled != is_enabled:
                rec.sudo().write({'is_moneris_go_preauth_enabled': is_enabled})

        super()._check_before_creating_new_session()

    # @api.depends('payment_method_ids')
    # def _compute_is_moneris_go_preauth_enabled(self):
    #     for rec in self:
    #         if any(rec.payment_method_ids.mapped('is_moneris_go_cloud')):
    #             rec.is_moneris_go_preauth_enabled = True
    #         else:
    #             rec.is_moneris_go_preauth_enabled = False



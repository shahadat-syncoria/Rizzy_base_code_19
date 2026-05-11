from datetime import datetime

from odoo import fields, models,  api,_
from odoo.exceptions import UserError
from odoo.addons.os_payment.payment_apps.payment_rotessa.utils.helper import _get_provider


class RotessaAccountMove(models.Model):
    _inherit = 'account.move'

    # {
    #     "customer_id": 193778,
    #     "amount": 100,
    #     "frequency": "Once",
    #     "process_date": "October 27, 2023",
    #     "installments": 1,
    #     "comment": "Membership fees"
    # }

    rotessa_customer_id = fields.Char(string="Rotessa Customer ID", related='partner_id.rotessa_cust_id',copy=False)
    rotessa_payment_frequency = fields.Selection([
        ("Once", "One time payment"),
        ("Weekly", "Every week"),
        ("Every_Other_Week", "Every two weeks"),
        ("Monthly", "Every month"),
        ("Every_Other_Month", "Every two months"),
        ("Quarterly", "Every 3 months"),
        ("Semi-Annually", "Every six months"),
        ("Yearly", "Once a year"),

    ], "Rotessa Payment Frequency", default="Once")

    rotessa_process_date = fields.Date(string="Rotessa process date",store=True)
    rotessa_transaction_sc_id = fields.Many2one('rotessa.transaction.tracking',readonly=True)
    rotessa_transaction_state = fields.Selection(related='rotessa_transaction_sc_id.state')
    rotessa_transaction_comment = fields.Char("Comment")

    is_rotessa_active = fields.Boolean(
        compute="_compute_is_rotessa_active",
        store=False
    )

    @api.model
    def _is_rotessa_active(self):
        """Check if Rotessa provider exists (1 DB call per request)."""
        return bool(
            self.env['payment.provider'].sudo().search([('code', '=', 'rotessa'), ('state', '!=', 'disabled')], limit=1)
        )

    def _compute_is_rotessa_active(self):
        active = self._is_rotessa_active()
        for rec in self:
            rec.is_rotessa_active = active

    @api.constrains('rotessa_process_date')
    def constrain_process_date(self):
        for rec in self:
            if rec.rotessa_process_date and (rec.rotessa_process_date <= fields.Date.today()):
                raise UserError("Process date cannot in past!!")

    @api.model
    def _check_rotessa_payment_conditions(self):
        for rec in self:
            error_message = ''
            if rec.rotessa_transaction_state in ['Future','Pending']:
                raise UserError((f"For record {rec.re}:\n" + "Payment already in progress!"))
            if rec.rotessa_transaction_state in ['APPROVED']:
                raise UserError((f"For record {rec.re}:\n" + "Partial payment not supported for now! Coming soon..."))
            if not rec.rotessa_customer_id:
                error_message += 'No rotessa customer attached!\n'
            if not rec.rotessa_process_date:
                error_message += 'Process date not selected!\n'
            if not rec.rotessa_payment_frequency:
                error_message += 'Payment frequency not selected!\n'
            if rec.rotessa_payment_frequency != 'Once':
                error_message += 'Only one time payment supported!\n'
            if rec.rotessa_payment_frequency != 'Once':
                error_message += 'Only one time payment supported!\n'
            if  rec.move_type != 'out_invoice':
                error_message += 'Only supported for invoice payment!\n'



            if error_message != '':
                raise UserError(_(f"For record {rec.ref}:\n" + error_message))


    def action_register_rotessa_payment(self):
        provider_id = _get_provider(code='rotessa')
        for rec in self:
            rec._check_rotessa_payment_conditions()
            to_currency = self.env['res.currency'].search([('name', '=', 'CAD')])

            if rec.currency_id.name != 'CAD':
                converted_amount = rec.currency_id._convert(rec.amount_total, to_currency, rec.company_id,
                                                            fields.Date.today())
            else:
                converted_amount = rec.amount_total
            payload = {
                "customer_id": rec.rotessa_customer_id,
                "amount": converted_amount,
                "frequency": "Once",
                "process_date": rec.rotessa_process_date.strftime('%B %d, %Y'),
                "installments": 1,
                "comment": rec.rotessa_transaction_comment
            }
            response= provider_id._rotessa_make_request(
                endpoint='create_transaction_schedule',
                data=payload,
                method='POST'
            )


            tracking_id = self.env['rotessa.transaction.tracking'].create({
                'transaction_schedule_id': response.get('id'),
                'invoice_no': rec.id,
                'invoice_ref': rec.name,
                'invoice_partner_id': rec.partner_id.id,
                'invoice_date': rec.invoice_date,
                'process_date': rec.rotessa_process_date,
                'state': 'Future',
                'status_reason': '',
                'provider_id': provider_id.id,
                'amount': rec.amount_total,

                'transaction_request_date': datetime.fromisoformat(
                    response.get('updated_at').replace('T', ' ').split('.')[0])
            }
            )
            rec.write({
                "rotessa_transaction_sc_id": tracking_id
            })
            rec.message_post(body=f"Rotessa: Payment Schedule created at {fields.Datetime.now()} and ID: response.get('id')")

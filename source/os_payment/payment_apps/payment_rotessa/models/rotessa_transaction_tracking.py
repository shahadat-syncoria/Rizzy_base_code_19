from odoo import fields, models, api
from odoo.exceptions import UserError


class RotessaTransactionTracking(models.Model):
    _name = 'rotessa.transaction.tracking'
    _description = "Rotessa Transaction Tracking"
    _rec_name = "transaction_schedule_id"

    transaction_schedule_id = fields.Integer("Transaction Schedule ID")
    invoice_no = fields.Many2one("account.move", "Invoice Number")
    invoice_ref = fields.Char("Reference")
    invoice_partner_id = fields.Many2one("res.partner", "Partner")

    invoice_date = fields.Date("Invoice Date")
    process_date = fields.Date("Process Date")
    state = fields.Selection(
        [
            ("Future", "Future"),
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Declined", "Declined"),
            ("Chargeback", "Chargeback"),
        ],
        "Transaction Status",
        default="Future",
    )
    status_reason = fields.Char("Status Reason")
    remain_settle_day = fields.Char("Remaining days to Settle")

    transaction_ids = fields.One2many(
        string="Transaction Ids",
        comodel_name="payment.transaction",
        inverse_name="rotessa_track_id",
    )
    transaction_id = fields.Many2one(
        "payment.transaction",
        string="Transaction Ids",
    )
    provider_id = fields.Many2one("payment.provider", "Provider")
    amount = fields.Float(string="Amount", digits=(6, 3), default=0.0)
    transaction_request_date = fields.Datetime(string="Requested time")
    last_cron_update = fields.Datetime("Last Cron Update",readonly=True)


    def _tx_rotessa_data_update(self):
        self.transaction_id.payment_id.unlink()
        self.transaction_id._set_done()
        # Immediately post-process the transaction as the post-processing will not be
        # triggered by a customer browsing the transaction from the portal.
        self.transaction_id._reconcile_after_done()

    def _invoice_rotessa_data_update(self):
        payment_method_line = self.provider_id.journal_id.inbound_payment_method_line_ids \
            .filtered(lambda l: l.code == 'rotessa')
        payment_values = {
            'amount': abs(self.amount),  # A tx may have a negative amount, but a payment must >= 0
            'payment_type': 'inbound',
            'currency_id': self.invoice_no.currency_id.id,
            'partner_id': self.invoice_no.partner_id.commercial_partner_id.id,
            'partner_type': 'customer',
            'journal_id': self.provider_id.journal_id.id,
            'company_id': self.provider_id.company_id.id,
            'payment_method_line_id': payment_method_line.id,
            'payment_reference':self.invoice_no.name,
            'memo': self.invoice_no.name,
        }
        payment = self.env['account.payment'].create(payment_values)
        payment.action_post()

        (payment.line_ids + self.invoice_no.line_ids).filtered(
            lambda line: line.account_id == payment.destination_account_id
                         and not line.reconciled
        ).reconcile()

    def update_transactions_status(self):
        for rec in self:
            data= {
                'transaction_schedule_id': rec.transaction_schedule_id
            }
            response = rec.provider_id._rotessa_make_request(
                # endpoint=f'/transaction_schedules/{rec.transaction_schedule_id}',
                endpoint='get_transaction_schedule',
                data=data,
            )
            if str(response.get('id')) in rec.provider_id.test_transaction_schedule_id.split(','):
                response.update({
                    "financial_transactions":[
                        {
                            "status":'Approved'
                        }
                    ]
                })
            # financial_transaction = [
            #     {
            #         "status": 'Approved'
            #     }
            # ] // dummy data
            financial_transaction = response.get('financial_transactions')
            if financial_transaction:
                financial_transaction_record = financial_transaction[0]
                if financial_transaction_record.get('status') == 'Approved':
                    if rec.transaction_id:
                        rec._tx_rotessa_data_update()
                    else:
                        rec._invoice_rotessa_data_update()

                rec.write({
                    'state': financial_transaction_record.get('status'),
                    'status_reason': financial_transaction_record.get('status_reason') if financial_transaction_record.get('status_reason') else '',
                    'last_cron_update': fields.Datetime.now()
                })




    # FIX: Change the update process. Update status by getting batch data.
    def batch_update_transactions_status(self):
        # transactions_ids = self.search([('state','not in',['Approved','Chargeback'])] ,order="transaction_schedule_id")
        transactions_ids = self.search([('process_date','<=',fields.Date.today()),('state','not in',['Approved','Chargeback'])] ,order="transaction_schedule_id")
        transactions_ids.update_transactions_status()


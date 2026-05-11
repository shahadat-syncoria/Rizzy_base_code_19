import json
import logging
import pprint

import requests

from odoo import  api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.addons.odoosync_base.utils.app_payment import AppPayment

_logger = logging.getLogger(__name__)


class PaymentProviderRotessa(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('rotessa', "Rotessa")], ondelete={'rotessa': 'set default'})
    test_transaction_schedule_id = fields.Char("Test Transaction Schedule ID")


    def write(self, vals):
        res = super(PaymentProviderRotessa, self).write(vals)
        if self.code == 'rotessa':
            if self.is_published:
                self.is_published = False

        return res
    def _get_rotessa_url(self):
        if self.state == 'enabled':
            return 'https://api.rotessa.com/v1'
        else:
            return 'https://sandbox-api.rotessa.com/v1'


    def _rotessa_make_request(self, endpoint, data=None,method=None):

        # complete_url = self._get_rotessa_url()+endpoint
        # headers = {
        #     'Authorization': f'Token token=xFnM7uXjxLsKzQGTv74dgA',
        #     'Content-Type': 'application/json'
        # }
        try:
            srm = AppPayment(service_name='rotessa', service_type=endpoint, service_key=self.token)
            srm.data = data
            response = srm.payment_process(company_id=self.company_id.id)
            if response.get('error') or 'errors_message' in response:
                error = response.get('error') if 'error' in response else response.get("errors_message")
                raise ValidationError((error))

        except Exception as e:
            raise ValidationError(
                "Rotessa: " + (str(e))
            )

        return response



    def _format_response(self, response, operation):
        if response and response.get('err_code'):
            return {
                'x_response_code': self.AUTH_ERROR_STATUS,
                'x_response_reason_text': response.get('err_msg')
            }
        else:
            return {
                'x_response_code': response.get('transactionResponse', {}).get('responseCode'),
                'x_trans_id': response.get('transactionResponse', {}).get('transId'),
                'x_type': operation,
            }

    def transaction_schedule_request(self, tx, token=None,invoice_id=None):
        """Rotessa send transaction schedule request for the given amount.
        """
        to_currency = self.env['res.currency'].search([('name', '=', 'CAD')])

        if tx.currency_id.name != 'CAD':
            converted_amount = tx.currency_id._convert(tx.amount, to_currency, tx.company_id, fields.Date.today())
        else:
            converted_amount = tx.amount
        if token:
            payload = {
                "customer_id": token.rotessa_customer_id,
                "amount": converted_amount,
                "frequency": "Once",
                "process_date": invoice_id.rotessa_process_date.strftime('%B %d, %Y'),
                "installments": 1,
                "comment": invoice_id.rotessa_transaction_comment
            }
        response = self._rotessa_make_request(
            endpoint='create_transaction_schedule',
            data=payload,
        )

        return response





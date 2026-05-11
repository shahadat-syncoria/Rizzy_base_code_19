from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
from requests.auth import HTTPBasicAuth
from odoo.http import request
import logging
_logger = logging.getLogger(__name__)
from odoo.addons.odoosync_base.utils.app_payment import AppPayment


class ResolvePay(models.Model):
    _name = 'resolvepay.instance'
    _description = 'Resolvepay Instance'

    name = fields.Char(string='Instance Name', default='ResolvePay', required=True)
    token = fields.Char(string='Token')
    company_id = fields.Many2one('res.company', required=True)
    connect_state = fields.Selection([
        ('draft', 'Not Confirmed'),
        ('confirm', 'Confirmed')],
        default='draft', string='State')
    journal_id = fields.Many2one('account.journal', string='Journal')
    template_id = fields.Many2one('ir.actions.report', string='PDF to Send', help='This PDF version will be sent when submitting an invoice', domain=[('model', '=', 'account.move')])
    _sql_constraints = [
        ('instance_name_uniq', 'unique (name)', 'Instance name must be unique.')
    ]

    def check_connect_access(self):
        srm = AppPayment(service_name='resolve', service_type='get_customers', service_key=self.token)
        response = srm.payment_process(company_id=self.company_id.id)
        if response.get('results') and not response.get('error'):
            self.connect_state = 'confirm'
        else:
            raise ValidationError('Connect failed')

    def disconnect_access(self):
        self.connect_state = 'draft'

    def _post_request(self, payload, service_type=''):
        srm = AppPayment(service_name='resolve', service_type=service_type, service_key=self.token)
        srm.data = {
            'type': 'POST',
            'payload': payload
        }
        response = srm.resolvepay_api_call(company_id=self.company_id.id)
        if 'error' not in response:
            return response
        else:
            raise ValidationError(str(response.get('error')))
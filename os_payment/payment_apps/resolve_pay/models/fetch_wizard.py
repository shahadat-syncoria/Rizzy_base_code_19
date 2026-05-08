import logging
from dateutil import parser
from odoo import fields, models, exceptions, _
from odoo.exceptions import UserError, ValidationError
import time

_logger = logging.getLogger(__name__)


class ResolvepayFetchWizard(models.Model):
    _name = 'resolvepay.fetch.wizard'
    _description = 'Fetch Customer'

    instance_id = fields.Many2one(
        string='ResolvePay Instance',
        comodel_name='resolvepay.instance',
    )
    create_new = fields.Boolean(string='Create New Contact If Not Found')
    status = fields.Selection([('all', 'All'), ('active', 'Active'), ('archived', 'Archived')], 'Status', default='all')

    def fetch_customers_resolvepay(self):
        resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
        customer_count = 0
        res = resolvepay_instance._post_request({}, service_type='get_customers')
        page = 1
        count = res['count']
        limit = 100
        while customer_count < count:
            payload = {
                'limit': limit,
                'page': page
            }
            time.sleep(0.5)
            res = resolvepay_instance._post_request(payload, service_type='get_customers')
            if res.get('results'):
                page += 1
                customer_count += len(res.get('results'))
                customer_list = res.get('results')
                for customer in customer_list:
                    _logger.info(customer)
                    if not customer.get('email'):
                        continue
                    if self.status == 'active':
                        if customer['archived']:
                            continue
                    elif self.status == 'archived':
                        if not customer['archived']:
                            continue
                    partner = self.env['res.partner'].search([('email', '=', customer.get('email'))], limit=1)
                    if partner:
                        customer_value = {}
                        for key, value in customer.items():
                            if 'resolvepay_' + key in self._fields:
                                customer_value['resolvepay_' + key] = value
                        _logger.info(f'UPDATE CONTACT: {partner.name} {partner.id}')
                        partner.write(customer_value)
                    elif self.create_new:
                        try:
                            partner_dict = {}
                            partner_dict['resolvepay_id'] = customer.get('id')
                            partner_dict['street'] = customer.get('business_address')
                            partner_dict['city'] = customer.get('business_city')
                            state_id = self.env['res.country.state'].search([
                                ('code', '=', customer.get('business_state'))],
                                limit=1)
                            if state_id:
                                partner_dict['state_id'] = state_id.id
                            country_id = self.env['res.country'].search([
                                ('code', '=', customer.get('business_country'))],
                                limit=1)
                            if country_id:
                                partner_dict['country_id'] = country_id.id
                            partner_dict['zip'] = customer.get('business_zip')
                            partner_dict['email'] = customer.get('email')
                            partner_dict['phone'] = customer.get('business_ap_phone')
                            partner_dict['name'] = customer.get('business_name')
                            for key, value in customer.items():
                                if 'resolvepay_' + key in self.env['res.partner']._fields:
                                    partner_dict['resolvepay_' + key] = value
                            partner_id = self.env['res.partner'].with_context(res_partner_search_mode='customer').create(partner_dict)
                            _logger.info(f'CREATE CONTACT: {partner_id.name} {partner_id.id}')
                        except Exception as e:
                            _logger.error(e)
                            raise ValidationError('Error occurred: %s', e)

        _logger.info("Complete===>>>fetch_customers_resolvepay")


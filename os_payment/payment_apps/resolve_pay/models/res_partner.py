from odoo import models, fields, api, _
import requests
from odoo.exceptions import UserError, ValidationError
import json, time
from requests.auth import HTTPBasicAuth

import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    resolvepay_id = fields.Char(string='ResolvePay Customer Id', copy=False, tracking=True)
    resolvepay_created_at = fields.Char(string='Date the customer was created.')
    resolvepay_updated_at = fields.Char(string='Date the customer was last updated.')
    resolvepay_source = fields.Char(string='ResolvePay Source')
    resolvepay_business_address = fields.Char(string='Street address of the business primary location.')
    resolvepay_business_city = fields.Char(string='City of the business primary location.')
    resolvepay_business_state = fields.Char(string='State or province of the business primary location.')
    resolvepay_business_zip = fields.Char(string='US zip code of the business primary location.')
    resolvepay_business_country = fields.Char(string='Country of the business primary location according to the ISO 3166-1 alpha 2 standard.')
    resolvepay_business_age_range = fields.Char(string='String indicating age of the business in years.')
    resolvepay_business_ap_email = fields.Char(string='Email address of the business accounts payable person or department.')
    resolvepay_business_ap_phone = fields.Char(string='Phone number of the business accounts payable person or department.')
    resolvepay_business_name = fields.Char(string='Full legal name of the business being applied for.')
    resolvepay_business_trade_name = fields.Char(string='Trade name of the business')
    resolvepay_business_phone = fields.Char(string='Phone number of the business primary location.')
    resolvepay_business_type = fields.Char(string='String indicating the business type of legal entity.')
    resolvepay_email = fields.Char(string='Email of the customer applying for terms.')
    resolvepay_personal_name_first = fields.Char(string='First name of the person applying on behalf of the business.')
    resolvepay_personal_name_last = fields.Char(string='Last name of the person applying on behalf of the business.')
    resolvepay_personal_phone = fields.Char(string='Personal phone number of the customer representative applying for terms.')
    resolvepay_amount_approved = fields.Float(string='Total amount of the credit approved.')
    resolvepay_amount_authorized = fields.Float(string='Amount of the credit line reserved for authorized charges.')
    resolvepay_amount_available = fields.Float(string='Current amount of the credit line available for purchases.')
    resolvepay_amount_balance = fields.Float(string='Current balance on the customer credit line.')
    resolvepay_amount_unapplied_payments = fields.Float(string='Current amount of a customer unapplied payments.')
    resolvepay_default_terms = fields.Selection(selection=[
        ('net7', 'net7'),
        ('net10', 'net10'),
        ('net10th', 'net10th'),
        ('net15', 'net15'),
        ('net30', 'net30'),
        ('net45', 'net45'),
        ('net60', 'net60'),
        ('net75', 'net75'),
        ('net90', 'net90'),
        ('net120', 'net120'),
        ('net180', 'net180')],
        string='Set default terms that will apply to this customer invoices. Can be overridden when requesting an advance.', tracking=True)
    resolvepay_advance_rate = fields.Float(string='Advance Rate (%)', tracking=True, help='The advance rate that will be used to determine the amount advanced for this customer invoices.')
    resolvepay_credit_status = fields.Char(string='Current credit status of this customer', tracking=True)
    resolvepay_net_terms_status = fields.Char(string='Current net terms enrollment status of this customer.', tracking=True)
    resolvepay_net_terms_enrollment_url = fields.Char(string='The URL for a customer to complete enrollment requirements when net_terms_status is pending_enrollment.')
    resolvepay_net_terms_enrollment_expires_at = fields.Char(string='The date by which the customer must be enrolled in this net terms offer')
    resolvepay_credit_check_requested_at = fields.Char(string='The date a credit check was requested.')
    resolvepay_archived = fields.Char(string='Indicating if customer is archived.', tracking=True)

    def create_customer_resolvepay(self):
        for partner in self.filtered(lambda p: not p.resolvepay_id):
            if partner.type == 'contact':
                required_fields = (partner.street, partner.city, partner.state_id, partner.zip, partner.country_id, partner.email)
                if not any(required_fields):
                    raise ValidationError('Street/City/State/Zip/Country/Email are required')
                resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
                partner_data = dict(
                    business_address=partner.street,
                    business_city=partner.city,
                    business_state=partner.state_id.code,
                    business_zip=partner.zip,
                    business_country=partner.country_id.code,
                    business_ap_email=partner.email,
                    business_ap_phone=partner.phone or partner.mobile or '',
                    business_name=partner.name,
                    email=partner.email,
                    default_terms=partner.resolvepay_default_terms,
                )
                if resolvepay_instance:
                    res = resolvepay_instance._post_request(partner_data, service_type='create_customer')
                    customer_value = {}
                    for key, value in res.items():
                        if 'resolvepay_' + key in self._fields:
                            customer_value['resolvepay_' + key] = value
                    partner.write(customer_value)
                else:
                    raise UserError('There is no ResolvePay instance')

    def update_customer_resolvepay(self):
        for partner in self:
            if partner.resolvepay_id:
                required_fields = (partner.street, partner.city, partner.state_id, partner.zip, partner.country_id, partner.email)
                if not any(required_fields):
                    raise ValidationError('Street/City/State/Zip/Country/Email are required')
                resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
                partner_data = dict(
                    customer_id=partner.resolvepay_id,
                    business_address=partner.street,
                    business_city=partner.city,
                    business_state=partner.state_id.code,
                    business_zip=partner.zip,
                    business_country=partner.country_id.code,
                    business_ap_email=partner.email,
                    business_ap_phone=partner.phone or partner.mobile or '',
                    business_name=partner.name,
                    email=partner.email,
                    default_terms=partner.resolvepay_default_terms,
                )
                if resolvepay_instance:
                    _logger.info("UPDATE CONTACT INFO TO RESOLVEPAY")
                    _logger.info(partner_data)
                    res = resolvepay_instance._post_request(partner_data, service_type='update_customer')
                    customer_value = {}
                    for key, value in res.items():
                        if 'resolvepay_' + key in self._fields:
                            customer_value['resolvepay_' + key] = value
                    partner.write(customer_value)
                else:
                    raise UserError('There is no ResolvePay instance')

    def action_update_resolvepay_contact_info(self):
        partners = self.env['res.partner'].search([])
        to_update = partners.filtered(lambda p: p.resolvepay_id)
        if not to_update:
            return
        for rec in to_update:
            try:
                time.sleep(0.5)
                rec.fetch_customer_resolvepay()
            except Exception as e:
                _logger.error(e)
                continue

    def fetch_customer_resolvepay(self):
        for partner in self:
            if not partner.resolvepay_id:
                raise ValidationError('Customer does not have Resolve Pay ID. Cannot update customer ' + partner.name)
            resolvepay_instance = self.env['resolvepay.instance'].search([('connect_state', '=', 'confirm')], limit=1)
            if resolvepay_instance:
                payload = {
                    'customer_id': partner.resolvepay_id
                }
                res = resolvepay_instance._post_request(payload, service_type='get_customer')
                customer_value = {}
                for key, value in res.items():
                    if 'resolvepay_' + key in self._fields:
                        customer_value['resolvepay_' + key] = value
                partner.write(customer_value)
            else:
                raise UserError('There is no ResolvePay instance')

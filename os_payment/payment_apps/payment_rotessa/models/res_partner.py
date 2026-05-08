import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
import json
from odoo.addons.os_payment.payment_apps.payment_rotessa.utils.helper import _get_provider

_logger = logging.getLogger(__name__)


class ResPartnerBankRotessa(models.Model):
    _inherit = 'res.partner.bank'

    bank_transit_no = fields.Char(
        string="Bank Transit No",
    )


class ResPartnersRotessa(models.Model):
    _inherit = 'res.partner'

    rotessa_authorization_type = fields.Selection([("online", "Online"), ("in_person", "In Person")])
    rotessa_cust_id = fields.Char("Rotessa Customer ID")
    rotessa_bank_id = fields.Many2one('res.partner.bank', "Rotessa Bank ID", domain="[('partner_id', '=', id)]")

    rotessa_institution_number = fields.Char("Institution Number", related='rotessa_bank_id.bank_id.bic')
    rotessa_transit_number = fields.Char("Transit Number", related='rotessa_bank_id.bank_transit_no')
    rotessa_cust_identf_number = fields.Integer("Rotessa customer identification numer", related='id')

    is_rotessa_active = fields.Boolean(
        compute="_compute_is_rotessa_active",
        store=False
    )

    @api.model
    def _is_rotessa_active(self):
        """Check if Rotessa provider exists (1 DB call per request)."""
        return bool(
            self.env['payment.provider'].sudo().search([('code', '=', 'rotessa'),('state','!=','disabled')], limit=1)
        )

    def _compute_is_rotessa_active(self):
        active = self._is_rotessa_active()
        for rec in self:
            rec.is_rotessa_active = active


    @api.model
    def _check_conditions(self):
        error_message = ''
        if not self.rotessa_bank_id:
            raise UserError((f"For  {self.name}:\n" + "No Bank account selected for rotessa!"))
        elif not (self.rotessa_institution_number and self.rotessa_transit_number):
            raise UserError((f"For  {self.name}:\n" + "No Institution/Transit no provided!"))

        if not len(self.rotessa_bank_id.acc_number) == 9:
            error_message += 'Account number must be 9 digits!\n'
        if not len(self.rotessa_institution_number) == 3:
            error_message += 'Bank institution number must be 3 digits!\n'
        if not len(self.rotessa_transit_number) == 5:
            error_message += 'Bank transit  number must be 5 digits!\n'
        if not self.rotessa_authorization_type:
            error_message += 'Please select authorization type!\n'
        if self.rotessa_cust_id:
            error_message += 'Customer already created\n'

        if error_message != '':
            raise UserError((f"For record {self.name}:\n" + error_message))

    def action_create_rotessa_customer(self):
        """
        Create customer based on existence
        :return: True
        """
        provider_id = _get_provider(code='rotessa')

        for rec in self:
            # Check for incomplete information
            rec._check_conditions()
            rotessa_bank = rec.rotessa_bank_id

            payload = {
                # "custom_identifier": f"{rec.id}",
                "email": f"{rec.email or ''}",
                "name": f"{rec.name}",
                "bank_name": f"{rotessa_bank.bank_id.name}",
                "transit_number": f"{rec.rotessa_transit_number}",
                "institution_number": f"{rec.rotessa_institution_number}",
                "authorization_type": dict(self._fields['rotessa_authorization_type'].selection).get(
                    self.rotessa_authorization_type),
                "account_number": f"{rotessa_bank.acc_number}",
                "address": {
                    "address_1": f"{rec.street or ''}",
                    "address_2": f"{rec.street2 or ''}",
                    "city": f"{rec.city}",
                    "province_code": f"{rec.state_id.code}",
                    "postal_code": f"{rec.zip}",
                }
            }
            response = provider_id._rotessa_make_request(
                endpoint='create_customers',
                data=payload,
            )
            rec.write(
                {
                    "rotessa_cust_id": response.get('id')
                }
            )
            self.env['payment.token'].create({
                'provider_id': provider_id.id,
                'payment_details': rec.name+f"{rotessa_bank.acc_number[-3:]}",
                'rotessa_customer_id': rec.rotessa_cust_id,
                'partner_id': rec.id,
                'provider_ref': "rotessa-"+rec.rotessa_cust_id[-2:],
                # 'verified': True, // depricated on 17
                "payment_method_id":provider_id.id

            })

            rec.message_post(body=f"Rotessa Customer Successfully Created.ID:{rec.rotessa_cust_id}")

    def action_update_rotessa_customer(self):
        pass

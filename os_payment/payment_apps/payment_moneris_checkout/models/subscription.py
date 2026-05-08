# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import logging

from odoo import api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_subscription_payment(self):
        for rec in self:
            provider = self.env['payment.provider'].sudo().search(
                [
                    ('code', '=', 'monerischeckout'),
                    ('company_id', '=', rec.company_id.id),
                ],
                limit=1,
            )
            if provider and rec._moneris_recurring_charge(provider):
                continue
            rec._send_card_email()

        # For all invoices (selected)
        #     if Customer has saved payment method
        #         Charge credit card for the invoice total
        #         If payment is successful
        #             Add payment to invoice, mark paid
        #         Else send email template: “Credit card could not be charged”**
        #     Else
        #         Send email template “Would you like to add your credit card?”

    def _send_card_email(self):
        """Send email template “Would you like to add your credit card?”"""
        print("Send email template “Would you like to add your credit card?”")
        self.ensure_one()

        # determine subject and body in the portal user's language
        template = self.env.ref(
            'payment_moneris_checkout.email_template_add_card')
        print("template ====>>>>", template)
        if not template:
            raise UserError(
                ('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.user_id.sudo().lang
        partner = self.partner_id
        print("lang ====>>>>", lang)
        print("partner ====>>>>", partner)

        # portal_url = partner.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[partner.id]
        partner.signup_prepare()
        # print("portal_url ====>>>>", portal_url)

        template.send_mail(self.id, force_send=True)
        print("template ====>>>>", template)
        return True

    def _send_paymentfailure_email(self):
        print("_send_paymentfailure_email")
        self.ensure_one()
        template = self.env.ref(
            'payment_moneris_checkout.email_template_subscription_invoice')
        print("template ====>>>>", template)
        if not template:
            raise UserError(
                _('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.user_id.sudo().lang
        partner = self.partner_id
        print("lang ====>>>>", lang)
        print("partner ====>>>>", partner)

        # portal_url = partner.with_context(signup_force_type_in_url='', lang=lang)._get_signup_url_for_action()[partner.id]
        partner.signup_prepare()
        # print("portal_url ====>>>>", portal_url)

        template.send_mail(self.id, force_send=True)
        print("template ====>>>>", template)
        return True

    def _get_moneris_journal_and_method_line(self):
        journal_domain = [
            ('company_id', '=', self.company_id.id),
            ('type', '=', 'bank'),
            ('inbound_payment_method_line_ids.payment_method_id.code', '=', 'monerischeckout'),
        ]
        journal = self.env['account.journal'].sudo().search(journal_domain, limit=1)
        if not journal:
            return False, False
        method_line = journal.inbound_payment_method_line_ids.filtered(
            lambda line: line.payment_method_id.code == 'monerischeckout'
        )[:1]
        return journal, method_line

    def _get_moneris_recurring_token(self, provider):
        self.ensure_one()
        partner_ids = {self.partner_id.id, self.partner_id.commercial_partner_id.id}
        return self.env['payment.token'].sudo().search([
            ('partner_id', 'in', list(partner_ids)),
            ('provider_id', '=', provider.id),
            ('active', '=', True),
            ('moneris_profile', '!=', False),
            ('moneris_recurring', '=', True),
        ], order='id desc', limit=1)

    def _moneris_recurring_charge(self, provider):
        self.ensure_one()
        if self.amount_residual <= 0:
            return False
        token = self._get_moneris_recurring_token(provider)
        if not token:
            return False
        values = self.get_register_vals(token, provider=provider)
        if not values:
            return False
        pay_reg_id = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.ids,
            active_id=self.id,
        ).sudo().create(values)
        pay_reg_id.action_create_payments()
        return True

    def get_register_vals(self, token_id, provider=None):
        journal, method_line = self._get_moneris_journal_and_method_line()
        if not journal or not method_line:
            _logger.warning(
                "Moneris recurring: no suitable journal/method line found for company %s",
                self.company_id.id,
            )
            return False
        vals = {
            'can_edit_wizard': False,
            'can_group_payments': False,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'source_amount': self.amount_residual,
            'source_amount_currency': self.amount_residual,
            'source_currency_id': self.currency_id.id,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'country_code': self.partner_id.country_id.code,
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
            'payment_token_id': token_id.id,
            'partner_bank_id': False,
            'group_payment': False,
            'amount': self.amount_residual,
            'currency_id': self.currency_id.id,
            'payment_date': fields.Datetime.now().date().strftime('%Y-%m-%d'), 
            'communication': self.name,
            'payment_difference_handling': 'open', 
            'writeoff_account_id': False, 
            'writeoff_label': 'Write-Off'
        
        }
        return vals

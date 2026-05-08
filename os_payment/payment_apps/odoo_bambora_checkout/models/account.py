# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api
from odoo.http import request
from odoo.exceptions import UserError
import logging
import pprint
import json
_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        res = {}
        domain = [('partner_id', '=', self.env.user.partner_id.id)]
        PayAcq = self.env['payment.provider']
        payacq_ids = PayAcq.sudo().search(
            [('code', '=', 'bamborachk'), ('company_id', 'in', self.env.user.company_ids.ids)])
        if self.journal_id.id in payacq_ids.journal_id.ids:
            domain.append(('bamborachk_profile', 'not in', (False, '')))
        _logger.info(domain)
        res = {'domain': {'token_id': domain}}
        self.inactive_mn_profiles()
        return res

    def inactive_mn_profiles(self):
        PayTkn = self.env['payment.token']
        payments = PayTkn.sudo().search(
            [('bamborachk_profile', 'in', (False, '')), ('provider_id.code', '=', 'bamborachk')])
        for paymnt in payments:
            paymnt.write({'active': False})


    bamborachk_move_name = fields.Char()
    payment_type_inbound = fields.Boolean()
    payment_type_outbound = fields.Boolean()

    @api.onchange('group_payment')
    def _onchange_mn_group_payment(self):
        _logger.info("\n _onchange_mn_group_payment")
        for rec in self:
            rec.bamborachk_move_name = ""
            if rec.group_payment == True and len(rec.line_ids.move_id) > 1:
                flag = False
                for line in rec.line_ids.move_id:
                    rec.bamborachk_move_name += line.name if flag == False else "," + line.name
                    flag = True

        _logger.info("\n--------------\n _onchange_group_payment: " +
                     rec.bamborachk_move_name + "\n-----------")

    @api.onchange('journal_id')
    def _onchange_mn_journal_id(self):
        _logger.info("\n _onchange_mn_journal_id")
        for rec in self:
            rec.bamborachk_move_name = ""
            if rec.group_payment == False and len(rec.line_ids.move_id) == 1:
                rec.bamborachk_move_name = rec.line_ids.move_id.name
            if rec.group_payment == True and len(rec.line_ids.move_id) > 1:
                flag = False
                for line in rec.line_ids.move_id:
                    rec.bamborachk_move_name += line.name if flag == False else "," + line.name
                    flag = True

            _logger.info("\n--------------\n _onchange_mn_journal_id: " +
                         rec.bamborachk_move_name + "\n-----------")

            if rec.journal_id and rec.journal_id.inbound_payment_method_line_ids:
                for payment_mthod in rec.journal_id.inbound_payment_method_line_ids:
                    if payment_mthod.code == 'bamborachk':
                        if rec.payment_type == 'inbound':
                            rec.payment_type_inbound = True
                        if rec.payment_type == 'outbound':
                            rec.payment_type_outbound = True

    @api.onchange('payment_method_id')
    def _onchange__mn_payment_method_id(self):
        for rec in self:
            rec.inactive_mn_profiles()
            rec.payment_type_inbound = rec.payment_type_outbound = False
            payment_type = rec.payment_method_id.payment_type
            if rec.payment_method_id.code == 'electronic':
                rec.payment_type_inbound = True if payment_type == 'inbound' else False
                rec.payment_type_outbound = True if payment_type == 'outbound' else False

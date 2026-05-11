# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
import json

from odoo import models, _, api
from odoo.tools import float_compare


SUPPORTED_CLOUD_TERMINALS = {
    'moneris_cloud',
    'moneris_cloud_go',
    'clover_cloud',
}


class SyncoriaConnectorPosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        result = super()._load_pos_data_models(config_id)
        for model_name in ('pos.order', 'pos.force.done.card.name'):
            if model_name not in result:
                result.append(model_name)
        return result

    def _loader_params_pos_order(self):
        return {
            'search_params': {
                'domain': [],
                'fields': [],
            },
        }

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        if result and 'search_params' in result and 'fields' in result['search_params']:
            load_fields = result['search_params']['fields']
            for field_name in ('enable_card_wise_journal', 'test_with_demo_response', 'demo_card_name', 'force_done_card_name_ids'):
                if field_name not in load_fields:
                    load_fields.append(field_name)
        return result

    def _loader_params_pos_force_done_card_name(self):
        return {
            'search_params': {
                'domain': [('active', '=', True), ('terminal', 'in', ['clover_cloud', 'moneris_cloud', 'moneris_cloud_go'])],
                'fields': ['id', 'name', 'code', 'sequence', 'terminal', 'active'],
            },
        }

    def _get_pos_ui_pos_force_done_card_name(self, params):
        return self.env['pos.force.done.card.name'].search_read(**params['search_params'])

    def _get_pos_ui_pos_order(self, params):
        return self.env['pos.order'].search_read(**params['search_params'])

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get('combine_receivables_bank') or {}
        eligible_methods = {
            payment_method.id: payment_method
            for payment_method in combine_receivables_bank
            if payment_method.enable_card_wise_journal
            and (payment_method.use_payment_terminal or '').strip().lower() in SUPPORTED_CLOUD_TERMINALS
        }
        if not eligible_methods:
            return super()._create_bank_payment_moves(data)

        default_combine_receivables_bank = {
            payment_method: amounts
            for payment_method, amounts in combine_receivables_bank.items()
            if payment_method.id not in eligible_methods
        }
        super_data = dict(data)
        super_data['combine_receivables_bank'] = default_combine_receivables_bank
        result = super()._create_bank_payment_moves(super_data)

        grouped_amounts = self._get_card_wise_grouped_amounts(set(eligible_methods))
        payment_method_to_receivable_lines = result.get('payment_method_to_receivable_lines', {})
        move_line_model = result.get('MoveLine', data.get('MoveLine'))
        bank_payment_method_diffs = data.get('bank_payment_method_diffs') or {}

        for payment_method_id, card_groups in grouped_amounts.items():
            payment_method = eligible_methods[payment_method_id]
            diff_amount = bank_payment_method_diffs.get(payment_method.id) or 0.0
            group_items = sorted(card_groups.items(), key=lambda item: item[0])
            for index, (card_name, amounts) in enumerate(group_items):
                combine_receivable_line = move_line_model.create(
                    self._get_combine_receivable_vals_for_card(
                        payment_method,
                        amounts['amount'],
                        amounts['amount_converted'],
                        card_name,
                    )
                )
                payment_receivable_line = self._create_combine_account_payment_for_card(
                    payment_method,
                    amounts,
                    diff_amount if index == 0 else 0.0,
                    card_name,
                )
                payment_method_to_receivable_lines[payment_method] = payment_method_to_receivable_lines.get(
                    payment_method, self.env['account.move.line']
                ) | combine_receivable_line | payment_receivable_line

        result['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
        return result

    def _get_card_wise_grouped_amounts(self, eligible_payment_method_ids):
        grouped = defaultdict(lambda: defaultdict(lambda: {'amount': 0.0, 'amount_converted': 0.0}))
        for order in self.order_ids:
            for payment in order.payment_ids:
                payment_method = payment.payment_method_id
                if payment_method.id not in eligible_payment_method_ids:
                    continue
                if payment.payment_status != 'done':
                    continue
                if float_compare(payment.amount, 0.0, precision_rounding=self.currency_id.rounding) <= 0:
                    continue

                normalized_card_name = self._extract_payment_card_name(payment)
                grouped[payment_method.id][normalized_card_name]['amount'] += payment.amount
                grouped[payment_method.id][normalized_card_name]['amount_converted'] += self._amount_converter(
                    payment.amount, self.stop_at, False
                )
        return grouped

    def _extract_payment_card_name(self, payment):
        payment_method = payment.payment_method_id
        if (
            payment_method
            and payment_method.enable_card_wise_journal
            and payment_method.test_with_demo_response
        ):
            demo_card_name = (payment_method.demo_card_name or '').strip().upper()
            return demo_card_name or 'UNKNOWN'

        clover_transaction_card_type = False
        clover_transaction_info = getattr(payment, 'clover_transaction_info', False)
        if clover_transaction_info:
            try:
                if isinstance(clover_transaction_info, str):
                    clover_transaction_info = json.loads(clover_transaction_info)
                if isinstance(clover_transaction_info, dict):
                    card_transaction = clover_transaction_info.get('cardTransaction') or {}
                    clover_transaction_card_type = (
                        card_transaction.get('cardType')
                        or card_transaction.get('extra', {}).get('authorizingNetworkName')
                        or card_transaction.get('type')
                    )
            except Exception:
                clover_transaction_card_type = False

        raw_card_name = (
            getattr(payment, 'card_name', False)
            or getattr(payment, 'moneris_cloud_cardname', False)
            or getattr(payment, 'moneris_cloud_apppreferredname', False)
            or getattr(payment, 'moneris_cloud_applabel', False)
            or getattr(payment, 'moneris_cloud_cardtype', False)
            or getattr(payment, 'card_type', False)
            or getattr(payment, 'clover_card_type', False)
            or clover_transaction_card_type
            or getattr(payment, 'clover_type', False)
        )
        return (raw_card_name or '').strip().upper() or 'UNKNOWN'

    def _get_combine_receivable_vals_for_card(self, payment_method, amount, amount_converted, card_name):
        partial_vals = {
            'account_id': self._get_receivable_account(payment_method).id,
            'move_id': self.move_id.id,
            'name': _('%(payment_method)s - %(card_name)s', payment_method=payment_method.name, card_name=card_name),
            'display_type': 'payment_term',
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _create_combine_account_payment_for_card(self, payment_method, amounts, diff_amount, card_name):
        outstanding_account = payment_method.outstanding_account_id
        destination_account = self._get_receivable_account(payment_method)
        memo = _(
            '%(card_name)s - Combine %(payment_method)s POS payments from %(session)s',
            card_name=card_name,
            payment_method=payment_method.name,
            session=self.name,
        )
        account_payment = self.env['account.payment'].with_context(pos_payment=True).create({
            'amount': abs(amounts['amount']),
            'journal_id': payment_method.journal_id.id,
            'force_outstanding_account_id': outstanding_account.id,
            'destination_account_id': destination_account.id,
            'memo': memo,
            'pos_payment_method_id': payment_method.id,
            'pos_session_id': self.id,
            'company_id': self.company_id.id,
        })

        accounting_installed = self.env['account.move']._get_invoice_in_payment_state() == 'in_payment'
        if not account_payment.outstanding_account_id and accounting_installed:
            account_payment.outstanding_account_id = account_payment._get_outstanding_account(account_payment.payment_type)

        if float_compare(amounts['amount'], 0.0, precision_rounding=self.currency_id.rounding) < 0:
            account_payment.write({
                'outstanding_account_id': account_payment.destination_account_id,
                'destination_account_id': account_payment.outstanding_account_id,
                'payment_type': 'outbound',
            })

        account_payment.action_post()
        if account_payment.move_id and account_payment.move_id.ref != memo:
            account_payment.move_id.ref = memo

        diff_amount_compare_to_zero = self.currency_id.compare_amounts(diff_amount, 0)
        if diff_amount_compare_to_zero != 0:
            self._apply_diff_on_account_payment_move(account_payment, payment_method, diff_amount)

        return account_payment.move_id.line_ids.filtered(
            lambda line: line.account_id == self._get_receivable_account(payment_method)
        )

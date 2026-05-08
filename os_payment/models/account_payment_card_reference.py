import ast
import json
import logging

from odoo import models

_logger = logging.getLogger(__name__)


SUPPORTED_CHECKOUT_PROVIDERS = {
    'monerischeckout',
    'clover_checkout',
}

CARD_TYPE_MAP = {
    'V': 'Visa',
    'VI': 'Visa',
    'VISA': 'Visa',
    'M': 'Mastercard',
    'MC': 'Mastercard',
    'MASTERCARD': 'Mastercard',
    'MASTER CARD': 'Mastercard',
    'AX': 'American Express',
    'AMEX': 'American Express',
    'AMERICANEXPRESS': 'American Express',
    'AMERICAN EXPRESS': 'American Express',
    'DC': "Diner's Card",
    'DINERS': "Diner's Card",
    'DINERSCLUB': "Diner's Card",
    'DINERS CLUB': "Diner's Card",
    'NO': 'Novus/Discover',
    'DISCOVER': 'Discover',
    'D': 'INTERAC Debit',
    'INTERAC': 'INTERAC Debit',
    'INTERACDEBIT': 'INTERAC Debit',
    'INTERAC DEBIT': 'INTERAC Debit',
    'C1': 'JCB',
    'JCB': 'JCB',
}

TRANSACTION_CARD_SOURCE_FIELDS = (
    'moneris_card_name',
    'clover_checkout_card_brand',
    'clover_checkout_card_type',
    'bamborachk_card_type',
)

PAYMENT_CARD_SOURCE_FIELDS = (
    'moneris_cloud_cardname',
    'moneris_cloud_apppreferredname',
    'moneris_cloud_applabel',
    'moneris_cloud_cardtype',
    'clover_card_type',
    'clover_type',
)

PAYMENT_CARD_TRIGGER_FIELDS = set(PAYMENT_CARD_SOURCE_FIELDS) | {
    'payment_transaction_id',
    'payment_method_line_id',
    'journal_id',
    'memo',
    'move_id',
    'clover_transaction_info',
    'clover_response',
}


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def _safe_field_value(self, field_name):
        self.ensure_one()
        return self[field_name] if field_name in self._fields else False

    def _get_payment_provider_code(self):
        self.ensure_one()
        transaction = self._safe_field_value('payment_transaction_id')
        if transaction:
            return transaction.provider_code

        payment_method_line = self._safe_field_value('payment_method_line_id')
        if payment_method_line and payment_method_line.payment_provider_id:
            return payment_method_line.payment_provider_id.code
        return False

    def _is_supported_card_reference_payment(self):
        self.ensure_one()
        provider_code = self._get_payment_provider_code()
        if provider_code in SUPPORTED_CHECKOUT_PROVIDERS:
            return True

        journal = self.journal_id
        return bool(
            journal
            and (
                ('use_cloud_terminal' in journal._fields and journal.use_cloud_terminal)
                or ('use_clover_terminal' in journal._fields and journal.use_clover_terminal)
            )
        )

    def _extract_card_name_from_transaction(self):
        self.ensure_one()
        transaction = self._safe_field_value('payment_transaction_id')
        if not transaction:
            return False

        for field_name in TRANSACTION_CARD_SOURCE_FIELDS:
            if field_name in transaction._fields and transaction[field_name]:
                return transaction[field_name]
        return False

    def _extract_card_name_from_clover_transaction_info(self):
        self.ensure_one()
        transaction_info = self._safe_field_value('clover_transaction_info')
        if not transaction_info:
            return False

        card_name = self._extract_card_name_from_payload(transaction_info)
        if card_name:
            return card_name

        return False

    def _parse_payload_to_dict(self, payload):
        if isinstance(payload, dict):
            return payload

        if not payload or not isinstance(payload, str):
            return False

        try:
            return json.loads(payload)
        except Exception:
            try:
                return ast.literal_eval(payload)
            except Exception:
                return False

    def _extract_card_name_from_card_transaction(self, card_transaction):
        if not isinstance(card_transaction, dict):
            return False
        extra = card_transaction.get('extra') or {}
        return (
            extra.get('authorizingNetworkName')
            or card_transaction.get('cardType')
            or card_transaction.get('type')
        )

    def _extract_card_name_from_payload(self, payload):
        payload_dict = self._parse_payload_to_dict(payload)
        if not isinstance(payload_dict, dict):
            return False

        card_transaction = payload_dict.get('cardTransaction')
        if isinstance(card_transaction, dict):
            return self._extract_card_name_from_card_transaction(card_transaction)

        # Some integrations store cardTransaction payload directly.
        return self._extract_card_name_from_card_transaction(payload_dict)

    def _extract_card_name_from_clover_response(self):
        self.ensure_one()
        clover_response = self._safe_field_value('clover_response')
        if not clover_response:
            return False

        try:
            response_dict = self._parse_payload_to_dict(clover_response)
            if not isinstance(response_dict, dict):
                return False

            data = response_dict.get('data') or {}
            payment = data.get('payment') or {}
            card_name = self._extract_card_name_from_card_transaction(payment.get('cardTransaction'))
            if card_name:
                return card_name

            refund = data.get('refund') or {}
            return self._extract_card_name_from_payload(refund.get('transactionInfo'))
        except Exception:
            _logger.debug("Unable to parse Clover response for payment %s", self.id, exc_info=True)
            return False

    def _normalize_card_name(self, raw_card_name):
        card_name = str(raw_card_name or '').strip()
        if not card_name:
            return False

        compact_key = card_name.upper().replace('_', ' ').strip()
        no_space_key = compact_key.replace(' ', '')
        mapped_name = CARD_TYPE_MAP.get(compact_key) or CARD_TYPE_MAP.get(no_space_key)
        if mapped_name:
            return mapped_name

        return ' '.join(word.capitalize() for word in compact_key.split())

    def _get_card_reference_prefix(self):
        self.ensure_one()
        if not self._is_supported_card_reference_payment():
            return False

        raw_card_name = self._extract_card_name_from_transaction()
        for field_name in PAYMENT_CARD_SOURCE_FIELDS:
            raw_card_name = raw_card_name or self._safe_field_value(field_name)
        raw_card_name = raw_card_name or self._extract_card_name_from_clover_transaction_info()
        raw_card_name = raw_card_name or self._extract_card_name_from_clover_response()
        return self._normalize_card_name(raw_card_name)

    def _prefix_card_reference_value(self, value, prefix):
        value = value or ''
        marker = '%s -- ' % prefix
        if value.startswith(marker):
            return value
        return '%s%s' % (marker, value) if value else prefix

    def _apply_card_reference_prefix(self):
        for payment in self:
            prefix = payment._get_card_reference_prefix()
            if not prefix:
                continue

            memo = payment.memo or ''
            prefixed_memo = payment._prefix_card_reference_value(memo, prefix)
            if prefixed_memo != memo:
                super(AccountPayment, payment.with_context(skip_card_reference_prefix=True)).write({
                    'memo': prefixed_memo,
                })

            move = payment.move_id
            if not move:
                continue

            ref = move.ref or ''
            prefixed_ref = payment._prefix_card_reference_value(ref, prefix)
            if prefixed_ref != ref:
                move.write({'ref': prefixed_ref})

            for line in move.line_ids:
                line_name = line.name or ''
                prefixed_line_name = payment._prefix_card_reference_value(line_name, prefix)
                if prefixed_line_name != line_name:
                    line.with_context(check_move_validity=False).write({'name': prefixed_line_name})

    def write(self, vals):
        res = super().write(vals)
        if (
            not self.env.context.get('skip_card_reference_prefix')
            and PAYMENT_CARD_TRIGGER_FIELDS.intersection(vals)
        ):
            self._apply_card_reference_prefix()
        return res

    def action_post(self):
        if not self.env.context.get('skip_card_reference_prefix'):
            self._apply_card_reference_prefix()
        res = super().action_post()
        if not self.env.context.get('skip_card_reference_prefix'):
            self._apply_card_reference_prefix()
        return res

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        line_vals_list = super()._prepare_move_line_default_vals(
            write_off_line_vals=write_off_line_vals,
            force_balance=force_balance,
        )
        prefix = self._get_card_reference_prefix()
        if not prefix:
            return line_vals_list

        for line_vals in line_vals_list:
            line_name = line_vals.get('name') or ''
            line_vals['name'] = self._prefix_card_reference_value(line_name, prefix)
        return line_vals_list

from odoo import fields, models


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    clover_checkout_card_brand = fields.Char('Clover Checkout Card Brand')
    clover_checkout_card_type = fields.Char('Clover Checkout Card Type')

    def _process_notification_data(self, notification_data):
        res = super()._process_notification_data(notification_data)
        for transaction in self:
            if transaction.provider_code != 'clover_checkout':
                continue

            source = notification_data.get('source') or {}
            card_brand = (
                source.get('brand')
                or source.get('card_brand')
                or source.get('cardBrand')
                or source.get('network')
            )
            card_type = (
                source.get('type')
                or source.get('card_type')
                or source.get('cardType')
                or notification_data.get('payment_method_details')
            )

            vals = {}
            if card_brand:
                vals['clover_checkout_card_brand'] = card_brand
            if card_type:
                vals['clover_checkout_card_type'] = card_type
            if vals:
                transaction.write(vals)
                if transaction.payment_id:
                    transaction.payment_id._apply_card_reference_prefix()
        return res

# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
from locale import currency
from odoo import models, fields, exceptions, api, _, Command
import re
import logging
from ..shopify.utils import to_shopify_gid

_logger = logging.getLogger(__name__)


class SaleOrderShopify(models.Model):
    _inherit = 'sale.order'

    shopify_id = fields.Char(string="Shopify Id", readonly=True,
                             store=True)
    shopify_order = fields.Char(readonly=True, store=True)
    shopify_status = fields.Char(string="shopify status", readonly=True)
    shopify_order_date = fields.Datetime(string="shopify Order Date")
    shopify_carrier_service = fields.Char(string="shopify Carrier Service")
    shopify_has_delivery = fields.Boolean(readonly=True, default=False, compute='shopifyhasdelviery')
    shopify_browser_ip = fields.Char(string='Browser IP', )
    shopify_buyer_accepts_marketing = fields.Boolean('Buyer Accepts Merketing', )
    shopify_cancel_reason = fields.Char('Cancel Reason', )
    shopify_cancelled_at = fields.Datetime('Cancel At', )
    shopify_cart_token = fields.Char('Cart Token', )
    shopify_checkout_token = fields.Char('Checkout Token', )
    shopify_currency = fields.Many2one(
        string='Shop Currency',
        comodel_name='res.currency',
        ondelete='restrict',
    )
    shopify_financial_status = fields.Selection(
        string='Financial Status',
        selection=[('pending', 'Pending'),
                   ('authorized', 'Authorized'),
                   ('partially_paid', 'Partially Paid'),
                   ('paid', 'Paid'),
                   ('partially_refunded', 'Partially Refunded'),
                   ('voided', 'Voided'),
                   ('refunded', 'Refunded')
                   ], default='pending'

    )
    shopify_fulfillment_status = fields.Char('Fullfillment Status', )
    shopify_track_updated = fields.Boolean(default=False, readonly=True, )
    shopify_transaction_ids = fields.One2many(
        string='Shopify Transaction',
        comodel_name='shopify.transactions',
        inverse_name='sale_id',
    )
    shopify_refund_ids = fields.One2many(
        string='Shopify Refunds',
        comodel_name='shopify.refunds',
        inverse_name='sale_id',
    )
    shopify_refund_transaction_ids = fields.One2many(
        string='Shopify Refunds Transaction',
        comodel_name='shopify.refunds.transaction',
        inverse_name='sale_id',
    )
    shopify_fulfilment_ids = fields.One2many(
        string='Shopify Fulfilment',
        comodel_name='shopify.fulfilment',
        inverse_name='sale_order_id',
    )
    shopify_is_invoice = fields.Boolean(string="Is shopify invoice paid?", default=False)
    shopify_is_refund = fields.Boolean(string="Is shopify credit note paid?", default=False)
    transaction_fee_tax_amount = fields.Monetary()
    transaction_fee_total_amount = fields.Monetary()
    refund_fee_tax_amount = fields.Monetary()
    refund_fee_total_amount = fields.Monetary()
    shopify_tag_ids = fields.Many2many('crm.tag', string="Shopify Tags")
    coupon_ids = fields.Many2many('shopify.coupon', string="Shopify Coupons")
    shopify_sale_channel = fields.Selection(string='Shopify Sale Channel', selection=[('pos', 'Point of Sale'),
                                                                                      ('web', 'Online Store'),
                                                                                      ('subscription_contract', 'Subscription Contract'),
                                                                                      ('shopify_draft_order',
                                                                                       'Draft Order'),
                                                                                      ('Matrixify App', 'Matrixify App')])
    shopify_err_tag_ids = fields.Many2many('shopify.err.tag', string='Shopify Error Tags')

    def fetch_shopify_payments(self):
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.marketplace_instance_id
                if not getattr(marketplace_instance_id, "use_graphql", False):
                    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
                order_data = rec._shopify_get_order_finance_graphql()
                transactions = order_data.get('transactions') or []
                if transactions:
                    message += '\nLength of Transaction List-{}'.format(len(transactions))
                    tran_recs = rec.process_shopify_transactions(transactions)
                    message += '\nTransaction Record Created-{}'.format(len(tran_recs))
                _logger.info(message)

    def process_shopify_transactions(self, transactions):
        tran_recs = []
        for transaction in transactions:
            sp_tran = self.env['shopify.transactions'].sudo()
            tran_id = sp_tran.search([('shopify_id', '=', transaction['id'])])
            if not tran_id and transaction.get('kind') != 'refund':
                vals = {
                    'sale_id': self.id,
                    'shopify_instance_id': self.marketplace_instance_id.id,
                }
                transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                for key, value in transaction.items():
                    if 'shopify_' + str(key) in list(sp_tran._fields) and key not in ['receipt', 'payment_details']:
                        vals['shopify_' + str(key)] = str(value)

                receipt_vals_list = []
                payment_details_vals_list = []

                try:
                    exchange_rate = "1.0000"
                    if transaction.get('currency'):
                        if transaction.get('currency') == self.pricelist_id.currency_id.name:
                            exchange_rate = "1.0000"
                            vals['shopify_exchange_rate'] = exchange_rate
                        else:
                            _logger.info("Transaction Currency do not match with Sale Order Pricelist Currency")
                except Exception as e:
                    _logger.warning("Exception-{}".format(e.args))

                if transaction.get('receipt'):
                    if type(transaction.get('receipt')) == dict:
                        receipt = transaction.get('receipt')
                        if receipt:
                            receipt_vals = {}
                            receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                            for key, value in receipt.items():
                                if key in receipt_fields:
                                    receipt_vals[key] = value
                            metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='sale')
                            if metadata_vals_list:
                                receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list

                            receipt_vals_list += [receipt_vals]
                            ########################################################################################################
                            try:
                                # Populate Exchange Rate:
                                if receipt.get('charges', {}).get('data', {}) and transaction.get(
                                        'amount') and receipt.get('amount'):
                                    if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                        data = receipt.get('charges', {}).get('data', {})
                                        for data_item in data:
                                            if float(transaction.get('amount')) == float(data_item.get('amount') / 100):
                                                if data_item.get('balance_transaction', {}).get('exchange_rate'):
                                                    vals['shopify_exchange_rate'] = data_item.get('balance_transaction',
                                                                                                  {}).get(
                                                        'exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))

                                    if float(transaction.get('amount')) == float(receipt.get('amount')):
                                        new_data = receipt.get('charges', {}).get('data', {})
                                        for data_items in new_data:
                                            if float(transaction.get('amount')) == float(
                                                    data_items.get('amount') / 100):
                                                if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                    vals['shopify_exchange_rate'] = data_items.get(
                                                        'balance_transaction', {}).get('exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))
                                            elif float(transaction.get('amount')) == float(data_items.get('amount')):
                                                if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                    vals['shopify_exchange_rate'] = data_items.get(
                                                        'balance_transaction', {}).get('exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))
                                                    vals['shopify_amount'] = float(data_items.get('amount') / 100)





                            except Exception as e:
                                _logger.warning("Exception-{}".format(e.args))
                            #######################################################################################################

                    if type(transaction.get('receipt')) == list:
                        for receipt in transaction.get('receipt'):
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value
                                metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='sale')
                                if metadata_vals_list:
                                    receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                receipt_vals_list += [receipt_vals]

                                ########################################################################################################
                                try:
                                    # Populate Exchange Rate:
                                    if receipt.get('charges', {}).get('data', {}) and transaction.get(
                                            'amount') and receipt.get('amount'):
                                        if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                            data = receipt.get('charges', {}).get('data', {})
                                            for data_item in data:
                                                if float(transaction.get('amount')) == float(
                                                        data_item.get('amount') / 100):
                                                    if data_item.get('balance_transaction', {}).get('exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_item.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))

                                        if float(transaction.get('amount')) == float(receipt.get('amount')):
                                            new_data = receipt.get('charges', {}).get('data', {})
                                            for data_items in new_data:
                                                if float(transaction.get('amount')) == float(
                                                        data_items.get('amount') / 100):
                                                    if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                elif float(transaction.get('amount')) == float(
                                                        data_items.get('amount')):
                                                    if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                        vals['shopify_amount'] = float(data_items.get('amount') / 100)

                                except Exception as e:
                                    _logger.warning("Exception-{}".format(e.args))
                                #######################################################################################################

                if transaction.get('payment_details'):
                    if type(transaction.get('payment_details')) == dict:
                        payment_details = transaction.get('payment_details')
                        if payment_details:
                            payment_details_vals = {}
                            payment_details_fields = list(self.env['shopify.payment.details']._fields)
                            for key, value in payment_details.items():
                                if key in payment_details_fields:
                                    payment_details_vals[key] = value
                            payment_details_vals_list += [payment_details_vals]

                    if type(transaction.get('payment_details')) == list:
                        for payment_details in transaction.get('payment_details'):
                            if payment_details:
                                payment_details_vals = {}
                                payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                for key, value in payment_details.items():
                                    if key in payment_details_fields:
                                        payment_details_vals[key] = value
                                payment_details_vals_list += [payment_details_vals]

                tran_id = sp_tran.create(vals)
                if receipt_vals_list:
                    for rv in receipt_vals_list:
                        rv['shopify_instance_id'] = self.marketplace_instance_id.id
                    receipt_id = self.env['shopify.payment.receipt'].create(receipt_vals_list)
                    if tran_id and receipt_id:
                        tran_id.shopify_payment_receipt_id = receipt_id[0].id

                if payment_details_vals_list:
                    for pdv in payment_details_vals_list:
                        pdv['shopify_instance_id'] = self.marketplace_instance_id.id
                    detail_id = self.env['shopify.payment.details'].create(payment_details_vals_list)
                    if tran_id and detail_id:
                        tran_id.shopify_payment_details_id = detail_id[0].id

                tran_recs.append(tran_id.id)

            if tran_id and transaction.get(
                    'kind') != 'refund' and tran_id.shopify_status == 'success' and not tran_id.shopify_exchange_rate:
                marketplace_instance_id = self.marketplace_instance_id
                domain = [('shopify_id', '=', tran_id.shopify_order_id)]
                domain += [('instance_id', '=', marketplace_instance_id.id)]
                feed_order_id = self.env['shopify.feed.orders'].sudo().search(domain, limit=1)
                try:
                    order_data = json.loads(feed_order_id.order_data) if feed_order_id and feed_order_id.order_data else {}
                    price_set = order_data.get('current_total_price_set') or {}
                    shop_amt = float((price_set.get('shop_money') or {}).get('amount') or 0)
                    pres_amt = float((price_set.get('presentment_money') or {}).get('amount') or 0)
                    if shop_amt and pres_amt:
                        tran_id.shopify_exchange_rate = shop_amt / pres_amt
                except Exception as e:
                    _logger.warning("Could not compute exchange rate for transaction %s: %s", tran_id.id, e)
        return tran_recs

    def process_receipt_metadata(self, receipt, tran_type):
        vals_list = []
        print("tran_type===>>>", tran_type)
        if receipt.get('charges', {}).get('data', {}):
            data = receipt.get('charges', {}).get('data', {})
            for data_item in data:
                vals = data_item.get('metadata')
                if vals:
                    vals.update({
                        'name': self.env['ir.sequence'].next_by_code('shopify.payment.receipt.metadata'),
                        'shopify_instance_id': self.marketplace_instance_id.id,
                        'company_id': self.company_id.id,
                        'sale_id': self.id,
                        'transaction_type': tran_type
                    })
                    if data_item.get('currency'):
                        currency = data_item.get('currency').upper()
                        print("currency===>>>", currency)
                        currency_id = self.env['res.currency'].sudo().search([('name', '=', currency)], limit=1)
                        print("currency_id===>>>", currency_id)
                        if currency_id:
                            vals['currency_id'] = currency_id.id

                    print("vals===>>>", vals)
                    # transaction_fee_total_amount: Penny Values to Decimal Value
                    # transaction_fee_tax_amount: Penny Values to Decimal Value
                    if vals.get('transaction_fee_total_amount'):
                        if float(vals.get('transaction_fee_total_amount')) > 0:
                            vals['transaction_fee_total_amount'] = float(vals.get('transaction_fee_total_amount')) / 100
                    if vals.get('transaction_fee_tax_amount'):
                        if float(vals.get('transaction_fee_tax_amount')) > 0:
                            vals['transaction_fee_tax_amount'] = float(vals.get('transaction_fee_tax_amount')) / 100

                    vals_list += [(0, 0, vals)]

        return vals_list

    def fetch_shopify_refunds(self):
        message = ''
        for rec in self:
            if rec.shopify_id:
                marketplace_instance_id = rec.marketplace_instance_id
                if not getattr(marketplace_instance_id, "use_graphql", False):
                    raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
                order_data = rec._shopify_get_order_finance_graphql()
                refunds = order_data.get('refunds') or []
                derived_from_transactions = False
                # Some stores/API responses may expose refund payments only via order.transactions(kind=refund).
                # Build a minimal synthetic refunds payload so refund transactions still get synced.
                if not refunds:
                    refund_tx = [t for t in (order_data.get('transactions') or []) if (t.get('kind') or '').lower() == 'refund']
                    if refund_tx:
                        derived_from_transactions = True
                        refunds = [{
                            # Keep a stable synthetic id to avoid empty/None headers.
                            "id": "derived-refund-%s" % rec.shopify_id,
                            "created_at": None,
                            "note": "Derived from order.transactions(kind=refund)",
                            "order_adjustments": [],
                            "refund_line_items": [],
                            "transactions": refund_tx,
                        }]
                        _logger.info(
                            "No refunds node returned for Shopify order %s; derived %s refund transaction(s) from order transactions.",
                            rec.shopify_id, len(refund_tx)
                        )
                if refunds:
                    message = '\nLength of Refund List-{}'.format(len(refunds))
                    refund_recs = []
                    if not derived_from_transactions:
                        refund_recs = self.process_shopify_refund(refunds)
                    refund_recs_transaction = self.process_shopify_refund_transaction(refunds)
                    message += 'Refund Record Created-{}\n'.format(len(refund_recs))
                    message += 'Refund Transaction Record Created-{}'.format(len(refund_recs_transaction))
                rec.message_post(body=_(message))

    def process_shopify_refund(self, refunds):
        refunds_recs = []
        for refund in refunds:
            sp_refunds = self.env['shopify.refunds'].sudo()
            refund_id = sp_refunds.search([('shopify_id', '=', refund['id'])])
            if not refund_id:
                vals = {
                    'sale_id': self.id,
                    'shopify_instance_id': self.marketplace_instance_id.id,
                }
                refund = {k: v for k, v in refund.items() if v is not False and v is not None}
                for key, value in refund.items():
                    if 'shopify_' + str(key) in list(sp_refunds._fields) and key not in ['receipt', 'payment_details']:
                        vals['shopify_' + str(key)] = str(value)
                vals['refund_json'] = json.dumps(refund)
                refund_id = sp_refunds.create(vals)
                refunds_recs.append(refund_id.id)
        return refunds_recs

    def process_shopify_refund_transaction(self, transactions):
        tran_recs = []
        for tran in transactions:
            # parent_refund_id = self.env['shopify.refunds'].search([('shopify_id', '=', str(tran.get('id')))])
            for transaction in tran.get('transactions'):
                sp_tran = self.env['shopify.refunds.transaction'].sudo()
                tran_id = sp_tran.search([('shopify_refund_id', '=', transaction['id'])])
                if not tran_id:
                    vals = {
                        'sale_id': self.id,
                        'shopify_instance_id': self.marketplace_instance_id.id,
                        # 'parent_refund_id': parent_refund_id.id if parent_refund_id else None
                    }
                    transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                    for key, value in transaction.items():
                        if 'shopify_refund_' + str(key) in list(sp_tran._fields) and key not in ['receipt',
                                                                                                 'payment_details']:
                            vals['shopify_refund_' + str(key)] = str(value)

                    receipt_vals_list = []
                    payment_details_vals_list = []

                    try:
                        exchange_rate = "1.0000"
                        if transaction.get('currency'):
                            if transaction.get('currency') == self.pricelist_id.currency_id.name:
                                exchange_rate = "1.0000"
                                vals['shopify_refund_exchange_rate'] = exchange_rate
                            else:
                                _logger.info("Transaction Currency do not match with Sale Order Pricelist Currency")
                    except Exception as e:
                        _logger.warning("Exception-{}".format(e.args))

                    if transaction.get('receipt'):
                        if type(transaction.get('receipt')) == dict:
                            receipt = transaction.get('receipt')
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value

                                metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='refund')
                                if metadata_vals_list:
                                    receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                receipt_vals_list += [receipt_vals]
                                ########################################################################################################
                                try:
                                    # Populate Exchange Rate:
                                    if transaction.get('amount') and receipt.get('amount'):
                                        if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                            data_item = receipt
                                            if data_item.get('balance_transaction', {}).get('exchange_rate'):
                                                vals['shopify_refund_exchange_rate'] = data_item.get(
                                                    'balance_transaction', {}).get('exchange_rate')
                                                print("exchange_rate===>>>{}".format(exchange_rate))

                                        if float(transaction.get('amount')) == float(receipt.get('amount')):
                                            data_items = receipt
                                            if float(transaction.get('amount')) == float(
                                                    data_items.get('amount') / 100):
                                                if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                    vals['shopify_refund_exchange_rate'] = data_items.get(
                                                        'balance_transaction', {}).get('exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))
                                            elif float(transaction.get('amount')) == float(data_items.get('amount')):
                                                if data_items.get('balance_transaction', {}).get('exchange_rate'):
                                                    vals['shopify_refund_exchange_rate'] = data_items.get(
                                                        'balance_transaction', {}).get('exchange_rate')
                                                    print("exchange_rate===>>>{}".format(exchange_rate))
                                                    vals['shopify_refund_amount'] = float(
                                                        data_items.get('amount') / 100)

                                except Exception as e:
                                    _logger.warning("Exception-{}".format(e.args))
                                #######################################################################################################

                        if type(transaction.get('receipt')) == list:
                            for receipt in transaction.get('receipt'):
                                if receipt:
                                    receipt_vals = {}
                                    receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                    for key, value in receipt.items():
                                        if key in receipt_fields:
                                            receipt_vals[key] = value

                                    metadata_vals_list = self.process_receipt_metadata(receipt=receipt,
                                                                                       tran_type='refund')
                                    if metadata_vals_list:
                                        receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                    receipt_vals_list += [receipt_vals]

                                    ########################################################################################################
                                    try:
                                        # Populate Exchange Rate:
                                        if transaction.get('amount') and receipt.get('amount'):
                                            if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                                data_item = receipt
                                                if float(transaction.get('amount')) == float(
                                                        data_item.get('amount') / 100):
                                                    if data_item.get('balance_transaction', {}).get('exchange_rate'):
                                                        vals['shopify_refund_exchange_rate'] = data_item.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))

                                            if float(transaction.get('amount')) == float(receipt.get('amount')):
                                                data_items = receipt

                                                if float(transaction.get('amount')) == float(
                                                        data_items.get('amount') / 100):
                                                    if data_items.get('balance_transaction', {}).get(
                                                            'exchange_rate'):
                                                        vals['shopify_refund_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                elif float(transaction.get('amount')) == float(
                                                        data_items.get('amount')):
                                                    if data_items.get('balance_transaction', {}).get(
                                                            'exchange_rate'):
                                                        vals['shopify_refund_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                        vals['shopify_refund_amount'] = float(
                                                            data_items.get('amount') / 100)

                                    except Exception as e:
                                        _logger.warning("Exception-{}".format(e.args))
                                    #######################################################################################################

                    if transaction.get('payment_details'):
                        if type(transaction.get('payment_details')) == dict:
                            payment_details = transaction.get('payment_details')
                            if payment_details:
                                payment_details_vals = {}
                                payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                for key, value in payment_details.items():
                                    if key in payment_details_fields:
                                        payment_details_vals[key] = value
                                payment_details_vals_list += [payment_details_vals]

                        if type(transaction.get('payment_details')) == list:
                            for payment_details in transaction.get('payment_details'):
                                if payment_details:
                                    payment_details_vals = {}
                                    payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                    for key, value in payment_details.items():
                                        if key in payment_details_fields:
                                            payment_details_vals[key] = value
                                    payment_details_vals_list += [payment_details_vals]



                    tran_id = sp_tran.create(vals)
                    if receipt_vals_list:
                        for rv in receipt_vals_list:
                            rv['shopify_instance_id'] = self.marketplace_instance_id.id
                        receipt_id = self.env['shopify.payment.receipt'].create(receipt_vals_list)
                        if tran_id and receipt_id:
                            tran_id.shopify_refund_payment_receipt_id = receipt_id[0].id

                    if payment_details_vals_list:
                        for pdv in payment_details_vals_list:
                            pdv['shopify_instance_id'] = self.marketplace_instance_id.id
                        detail_id = self.env['shopify.payment.details'].create(payment_details_vals_list)
                        if tran_id and detail_id:
                            tran_id.shopify_refund_payment_details_id = detail_id[0].id

                    tran_recs.append(tran_id.id)

                    if tran_id and tran_id.shopify_refund_status == 'success' and not tran_id.shopify_refund_exchange_rate:
                        marketplace_instance_id = self.marketplace_instance_id
                        domain = [('shopify_id', '=', tran_id.shopify_refund_order_id)]
                        domain += [('instance_id', '=', marketplace_instance_id.id)]
                        feed_order_id = self.env['shopify.feed.orders'].sudo().search(domain, limit=1)
                        try:
                            order_data = json.loads(feed_order_id.order_data) if feed_order_id and feed_order_id.order_data else {}
                            price_set = order_data.get('current_total_price_set') or {}
                            shop_amt = float((price_set.get('shop_money') or {}).get('amount') or 0)
                            pres_amt = float((price_set.get('presentment_money') or {}).get('amount') or 0)
                            if shop_amt and pres_amt:
                                tran_id.shopify_refund_exchange_rate = shop_amt / pres_amt
                        except Exception as e:
                            _logger.warning("Could not compute refund exchange rate for transaction %s: %s", tran_id.id, e)
                elif tran_id:
                    vals = {
                        # 'parent_refund_id': parent_refund_id.id if parent_refund_id else None
                    }
                    transaction = {k: v for k, v in transaction.items() if v is not False and v is not None}
                    for key, value in transaction.items():
                        if 'shopify_refund_' + str(key) in list(sp_tran._fields) and key not in ['receipt',
                                                                                                 'payment_details']:
                            vals['shopify_refund_' + str(key)] = str(value)

                    receipt_vals_list = []
                    payment_details_vals_list = []

                    try:
                        exchange_rate = "1.0000"
                        if transaction.get('currency'):
                            if transaction.get('currency') == self.pricelist_id.currency_id.name:
                                exchange_rate = "1.0000"
                                vals['shopify_refund_exchange_rate'] = exchange_rate
                            else:
                                _logger.info("Transaction Currency do not match with Sale Order Pricelist Currency")
                    except Exception as e:
                        _logger.warning("Exception-{}".format(e.args))

                    if transaction.get('receipt'):
                        if type(transaction.get('receipt')) == dict:
                            receipt = transaction.get('receipt')
                            if receipt:
                                receipt_vals = {}
                                receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                for key, value in receipt.items():
                                    if key in receipt_fields:
                                        receipt_vals[key] = value

                                metadata_vals_list = self.process_receipt_metadata(receipt=receipt, tran_type='refund')
                                if metadata_vals_list:
                                    receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                receipt_vals_list += [receipt_vals]
                                ########################################################################################################
                                try:
                                    # Populate Exchange Rate:
                                    if transaction.get(
                                            'amount') and receipt.get('amount'):
                                        if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                            data_item = receipt
                                            # if float(transaction.get('amount')) == float(
                                            #         data_item.get('amount') / 100):
                                            if data_item.get('balance_transaction', {}):
                                                vals['shopify_refund_exchange_rate'] = data_item.get(
                                                    'balance_transaction', {}).get('exchange_rate')
                                                print("exchange_rate===>>>{}".format(exchange_rate))

                                        if float(transaction.get('amount')) == float(receipt.get('amount')):
                                            # new_data = receipt.get('charge', {})
                                            # for data_items in new_data:
                                            if receipt.get('balance_transaction', {}).get('exchange_rate'):
                                                vals['shopify_exchange_rate'] = receipt.get(
                                                    'balance_transaction', {}).get('exchange_rate')
                                                print("exchange_rate===>>>{}".format(exchange_rate))
                                            # if float(transaction.get('amount')) == float(
                                            #         new_data.get('amount') / 100):
                                            #     if new_data.get('balance_transaction', {}).get('exchange_rate'):
                                            #         vals['shopify_exchange_rate'] = new_data.get(
                                            #             'balance_transaction', {}).get('exchange_rate')
                                            #         print("exchange_rate===>>>{}".format(exchange_rate))
                                            # elif float(transaction.get('amount')) == float(
                                            #         new_data.get('amount')):
                                            #     if new_data.get('balance_transaction', {}).get('exchange_rate'):
                                            #         vals['shopify_exchange_rate'] = new_data.get(
                                            #             'balance_transaction', {}).get('exchange_rate')
                                            #         print("exchange_rate===>>>{}".format(exchange_rate))
                                            #         vals['shopify_amount'] = float(new_data.get('amount') / 100)

                                except Exception as e:
                                    _logger.warning("Exception-{}".format(e.args))
                                #######################################################################################################

                        if type(transaction.get('receipt')) == list:
                            for receipt in transaction.get('receipt'):
                                if receipt:
                                    receipt_vals = {}
                                    receipt_fields = list(self.env['shopify.payment.receipt']._fields)
                                    for key, value in receipt.items():
                                        if key in receipt_fields:
                                            receipt_vals[key] = value

                                    metadata_vals_list = self.process_receipt_metadata(receipt=receipt,
                                                                                       tran_type='refund')
                                    if metadata_vals_list:
                                        receipt_vals['shopify_receipt_metadata_ids'] = metadata_vals_list
                                    receipt_vals_list += [receipt_vals]

                                    ########################################################################################################
                                    try:
                                        # Populate Exchange Rate:
                                        if transaction.get(
                                                'amount') and receipt.get('amount'):
                                            if float(transaction.get('amount')) == float(receipt.get('amount') / 100):
                                                data_item = receipt
                                                if float(transaction.get('amount')) == float(
                                                        data_item.get('amount') / 100):
                                                    if data_item.get('balance_transaction', {}).get(
                                                            'exchange_rate'):
                                                        vals['shopify_refund_exchange_rate'] = data_item.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))

                                            if float(transaction.get('amount')) == float(receipt.get('amount')):
                                                data_items = receipt

                                                if float(transaction.get('amount')) == float(
                                                        data_items.get('amount') / 100):
                                                    if data_items.get('balance_transaction', {}).get(
                                                            'exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                elif float(transaction.get('amount')) == float(
                                                        data_items.get('amount')):
                                                    if data_items.get('balance_transaction', {}).get(
                                                            'exchange_rate'):
                                                        vals['shopify_exchange_rate'] = data_items.get(
                                                            'balance_transaction', {}).get('exchange_rate')
                                                        print("exchange_rate===>>>{}".format(exchange_rate))
                                                        vals['shopify_amount'] = float(
                                                            data_items.get('amount') / 100)

                                    except Exception as e:
                                        _logger.warning("Exception-{}".format(e.args))
                                    #######################################################################################################

                    if transaction.get('payment_details'):
                        if type(transaction.get('payment_details')) == dict:
                            payment_details = transaction.get('payment_details')
                            if payment_details:
                                payment_details_vals = {}
                                payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                for key, value in payment_details.items():
                                    if key in payment_details_fields:
                                        payment_details_vals[key] = value
                                payment_details_vals_list += [payment_details_vals]

                        if type(transaction.get('payment_details')) == list:
                            for payment_details in transaction.get('payment_details'):
                                if payment_details:
                                    payment_details_vals = {}
                                    payment_details_fields = list(self.env['shopify.payment.details']._fields)
                                    for key, value in payment_details.items():
                                        if key in payment_details_fields:
                                            payment_details_vals[key] = value
                                    payment_details_vals_list += [payment_details_vals]

                    if tran_id and tran_id.shopify_refund_status == 'success' and not tran_id.shopify_refund_exchange_rate:
                        marketplace_instance_id = self.shopify_instance_id
                        domain = [('shopify_id', '=', tran_id.shopify_refund_order_id)]
                        domain += [('instance_id', '=', marketplace_instance_id.id)]
                        feed_order_id = self.env['shopify.feed.orders'].sudo().search(domain, limit=1)
                        try:
                            order_data = json.loads(feed_order_id.order_data) if feed_order_id and feed_order_id.order_data else {}
                            price_set = order_data.get('current_total_price_set') or {}
                            shop_amt = float((price_set.get('shop_money') or {}).get('amount') or 0)
                            pres_amt = float((price_set.get('presentment_money') or {}).get('amount') or 0)
                            if shop_amt and pres_amt:
                                tran_id.shopify_refund_exchange_rate = shop_amt / pres_amt
                        except Exception as e:
                            _logger.warning("Could not compute refund exchange rate for transaction %s: %s", tran_id.id, e)

                    tran_id.update(vals)
                    tran_recs.append(tran_id.id)
        return tran_recs

    def _force_lines_to_invoice_policy_order(self):
        """Ensure delivery-policy lines have a non-zero qty_to_invoice so that
        _create_invoices() includes them for Shopify orders that may not have
        been fulfilled yet."""
        for line in self.order_line:
            if (
                line.product_id.invoice_policy == 'delivery'
                and line.product_uom_qty > 0
                and line.qty_to_invoice == 0
            ):
                line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced

    def process_shopify_invoice(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        invoice_id = False
        for rec in self:
            success_tran_ids = rec.shopify_transaction_ids.filtered(lambda l: l.shopify_status == 'success')
            if success_tran_ids and not rec.shopify_is_invoice and rec.state != 'cancel':
                if rec.invoice_count == 0:
                    message += "\nCreating Invoice for Sale Order-{}".format(rec)
                    try:
                        with self.env.cr.savepoint():
                            rec._force_lines_to_invoice_policy_order()
                            invoice_id = rec._create_invoices()
                            invoice_id.shopify_order = rec.shopify_order
                            invoice_id.action_post()
                            if rec.shopify_order:
                                invoice_id.payment_reference = str(rec.shopify_order) + ' - ' + str(invoice_id.name)
                            invoice_id.write({'marketplace_instance_id': rec.marketplace_instance_id.id})
                            message += "\nInvoice-{} Posted for Sale Order-{}".format(invoice_id.name, rec.name)
                    except Exception as e:
                        msg = str(e)
                        _logger.warning(
                            "Failed to create/post invoice for Shopify sale order %s (%s): %s",
                            rec.name,
                            rec.shopify_order,
                            msg,
                        )
                        rec.message_post(
                            body=_("Shopify auto invoice failed for %s: %s") % (rec.name, msg)
                        )
                        if 'The entry is not balanced' in msg:
                            error_shopify_tag_id = self.env.ref("syncoria_shopify.discount_err", raise_if_not_found=False)
                            if error_shopify_tag_id:
                                rec.shopify_err_tag_ids |= error_shopify_tag_id
        return invoice_id, message

    def shopify_invoice_register_payments(self):
        message = ""
        move_id = False
        for rec in self:
            success_tran_ids = rec.shopify_transaction_ids.filtered(
                lambda l: l.shopify_status == 'success'
            )
            # Direct DB search avoids stale ORM cache when called immediately
            # after process_shopify_invoice() in the same transaction.
            invoices = self.env['account.move'].search([
                ('shopify_order', '=', rec.shopify_order),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
            ]) if rec.shopify_order else rec.invoice_ids.filtered(
                lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
            )
            if not invoices:
                _logger.warning(
                    "No posted invoice found for Shopify sale order %s — skipping payment registration.",
                    rec.name,
                )
                continue

            # Pick the invoice that still has an open balance; if multiple,
            # work through each one so partial payments apply correctly.
            open_invoices = invoices.filtered(lambda i: i.amount_residual > 0)
            if not open_invoices:
                _logger.info(
                    "Shopify sale order %s: all invoices already paid — nothing to register.",
                    rec.name,
                )
                rec.write({"shopify_is_invoice": True})
                continue

            move_id = open_invoices[0]

            for tran_id in success_tran_ids:
                try:
                    shopify_instance_id = tran_id.shopify_instance_id or rec.marketplace_instance_id

                    # Skip if a payment for this transaction already exists
                    if self.env['account.payment'].search([
                        ('shopify_id', '=', tran_id.shopify_id),
                        ('marketplace_instance_id', '=', shopify_instance_id.id),
                    ], limit=1):
                        continue

                    if not (float(tran_id.shopify_amount) > 0
                            and shopify_instance_id
                            and move_id.amount_residual > 0):
                        continue

                    # FX conversion when transaction currency differs from pricelist currency
                    shopify_amount = float(tran_id.shopify_amount)
                    try:
                        instance_currency = tran_id.shopify_instance_id.pricelist_id.currency_id.name
                        if tran_id.shopify_currency and tran_id.shopify_currency != instance_currency:
                            shopify_amount = float(tran_id.shopify_amount) * float(tran_id.shopify_exchange_rate)
                    except Exception:
                        pass

                    _logger.info(
                        "Shopify order %s: registering payment %.2f for gateway '%s' (transaction %s)",
                        rec.name, shopify_amount, tran_id.shopify_gateway, tran_id.shopify_id,
                    )

                    # Resolve journal: prefer gateway-specific mapping, then instance default
                    payment_method_mapping = shopify_instance_id.shopify_payment_method_mappings.filtered(
                        lambda s: s.name == tran_id.shopify_gateway
                    )
                    if payment_method_mapping:
                        journal_id = payment_method_mapping[0].journal_id.id or shopify_instance_id.marketplace_payment_journal_id.id
                    else:
                        journal_id = shopify_instance_id.marketplace_payment_journal_id.id
                        _logger.warning(
                            "Shopify order %s: no payment method mapping for gateway '%s' — "
                            "falling back to instance default journal.",
                            rec.name, tran_id.shopify_gateway,
                        )

                    if not journal_id:
                        _logger.warning(
                            "Shopify order %s: no journal configured for gateway '%s' — skipping transaction %s.",
                            rec.name, tran_id.shopify_gateway, tran_id.shopify_id,
                        )
                        continue

                    payment_date = (
                        tran_id.shopify_processed_at.split('T')[0]
                        if tran_id.shopify_processed_at
                        else fields.Date.context_today(self)
                    )

                    wizard_vals = {
                        'journal_id': journal_id,
                        'amount': shopify_amount,
                        'payment_date': payment_date,
                    }

                    payment_method_line_id = shopify_instance_id.marketplace_payment_journal_id.inbound_payment_method_line_ids.filtered(
                        lambda l: l.payment_method_id.id == shopify_instance_id.marketplace_inbound_method_id.id
                    )
                    if payment_method_line_id:
                        wizard_vals['payment_method_line_id'] = payment_method_line_id[0].id

                    pmt_wizard = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=move_id.ids,
                    ).create(wizard_vals)

                    payment = pmt_wizard._create_payments()
                    if payment:
                        payment.write({
                            'shopify_id': tran_id.shopify_id,
                            'marketplace_instance_id': shopify_instance_id.id,
                            'shopify_payment_gateway_names': tran_id.shopify_gateway,
                        })
                        _logger.info(
                            "Shopify order %s: payment %s created (%.2f via '%s').",
                            rec.name, payment.mapped('name'), shopify_amount, tran_id.shopify_gateway,
                        )

                    # Refresh residual after each payment
                    move_id.invalidate_recordset()
                    if move_id.payment_state in ['paid', 'in_payment']:
                        rec.write({"shopify_is_invoice": True})
                        break

                except Exception as e:
                    _logger.warning(
                        "Shopify order %s: failed to register payment for transaction %s — %s",
                        rec.name, tran_id.shopify_id, e,
                    )

        return move_id, message

    def process_shopify_refunds(self):
        self.fetch_shopify_refunds()
        self.process_shopify_credit_note()
        self.shopify_credit_note_register_payments()

    def process_shopify_credit_note(self):
        message = ""
        account_move = self.env['account.move'].sudo()
        move_id = False
        refund_move_id = False
        for rec in self:
            refund_ids = rec.shopify_refund_ids
            if refund_ids and rec.state != 'cancel':
                for refund in refund_ids:
                    refund_json = json.loads(refund.refund_json)
                    shopify_instance_id = rec.marketplace_instance_id
                    move_id = account_move.search([('shopify_order', '=', rec.shopify_order), ('move_type', "=", "out_invoice"), ('state', '=', 'posted')])
                    refund_move_id = account_move.search(
                        [('shopify_order', '=', rec.shopify_order), ('move_type', "=", "out_refund"), ('shopify_id', '=', refund.shopify_id)])
                    if move_id.payment_state in ['paid', 'in_payment'] and not refund_move_id:
                        message += "\nCreating Credit Note for Sale Order-{}".format(rec.name)
                        try:
                            with self.env.cr.savepoint():
                                wizard_vals = {
                                    'date': refund_json.get('created_at') or fields.Date.context_today(self),
                                    'reason': refund_json.get("note") or "Shopify Refund",
                                    'journal_id': move_id.journal_id.id
                                }
                                credit_note_wizard = self.env['account.move.reversal'].with_context(
                                    active_model='account.move',
                                    active_ids=move_id.ids).create(wizard_vals)
                                reversal = credit_note_wizard.sudo().reverse_moves()
                                refund_move_id = self.env['account.move'].browse(reversal['res_id'])
                                refund_move_id.write({'shopify_id': str(refund_json.get('id'))})
                                refund_line_items = refund_json.get('refund_line_items') or []
                                order_adjustments = refund_json.get('order_adjustments') or []
                                for line in refund_move_id.invoice_line_ids:
                                    qty = 0
                                    for refund_line_item in refund_line_items:
                                        if line.sale_line_ids.shopify_id == str(refund_line_item.get('line_item_id')):
                                            qty = refund_line_item.get('quantity')
                                            break
                                    refund_move_id.write(
                                        {'invoice_line_ids': [Command.update(line.id, {'quantity': qty})]})
                                for order_adjustment in order_adjustments:
                                    if order_adjustment.get('kind') == 'shipping_refund':
                                        service = self.env.ref('syncoria_shopify.shopify_shipping')
                                        shipping_line = refund_move_id.invoice_line_ids.filtered(
                                            lambda l: l.product_id == service)
                                        refund_move_id.write(
                                            {'invoice_line_ids': [Command.update(
                                                shipping_line.id,
                                                {'quantity': 1, 'price_unit': -float(order_adjustment.get('amount'))},
                                            )]})
                                    else:
                                        discrepancy_account = shopify_instance_id.refund_discrepancy_account_id
                                        if not discrepancy_account:
                                            _logger.warning(
                                                "Shopify order %s: 'Refund Discrepancy Account' is not set "
                                                "on the Shopify instance — skipping order_adjustment line '%s'.",
                                                rec.shopify_order,
                                                order_adjustment.get('reason'),
                                            )
                                            continue
                                        product_id = self.env.ref('syncoria_shopify.shopify_refund_discrepancy')
                                        refund_move_id.invoice_line_ids = [
                                            (0, 0, {
                                                'account_id': discrepancy_account.id,
                                                'name': order_adjustment.get('reason'),
                                                'quantity': 1,
                                                'product_id': product_id.id,
                                                'price_unit': -float(order_adjustment.get('amount')),
                                            })]
                        except Exception as e:
                            _logger.warning(
                                "Failed to create credit note for Shopify sale order %s: %s",
                                rec.name, e,
                            )
                            rec.message_post(
                                body=_("Shopify auto credit note failed for %s: %s") % (rec.name, e)
                            )
                            refund_move_id = False
                    if refund_move_id and refund_move_id.state != 'posted':
                        try:
                            refund_move_id.action_post()
                            message += "\nCredit Note-{} Posted for Sale Order-{}".format(refund_move_id, rec)
                        except Exception as e:
                            _logger.warning(
                                "Failed to post credit note %s for Shopify order %s: %s",
                                refund_move_id.name, rec.shopify_order, e,
                            )
        return refund_move_id, message

    def shopify_credit_note_register_payments(self):
        message = ""
        move_id = False
        for rec in self:
            refund_ids = rec.shopify_refund_ids
            for refund in refund_ids:
                refund_json = json.loads(refund.refund_json)
                refund_move_id = self.env['account.move'].search([('shopify_id', '=', str(refund_json.get('id')))])
                if not refund_move_id:
                    continue
                for tran_id in (refund_json.get('transactions') or []):
                    shopify_instance_id = rec.marketplace_instance_id
                    tran_shopify_id = str(tran_id.get('id') or '')
                    try:
                        tran_amount = float(tran_id.get('amount') or 0)
                    except (TypeError, ValueError):
                        continue
                    if not (tran_amount > 0 and shopify_instance_id
                            and refund_move_id.payment_state not in ('in_payment', 'paid')
                            and refund_move_id.amount_residual > 0):
                        continue

                    shopify_refund_amount = tran_amount

                    if tran_shopify_id:
                        existing_payment = self.env['account.payment'].sudo().search([
                            ('shopify_id', '=', tran_shopify_id),
                            ('marketplace_instance_id', '=', shopify_instance_id.id),
                        ], limit=1)
                        if existing_payment:
                            _logger.info(
                                "Refund payment for Shopify transaction %s already exists, skipping.",
                                tran_shopify_id,
                            )
                            continue

                    refund_payment_method_mapping = shopify_instance_id.shopify_refund_payment_method_mappings.filtered(
                        lambda s: s.name == tran_id.get("gateway"))
                    if not refund_payment_method_mapping:
                        _logger.warning(
                            "No refund payment method mapping found for gateway '%s' on order %s, skipping transaction.",
                            tran_id.get("gateway"), rec.name,
                        )
                        continue

                    wizard_vals = {
                        'journal_id': refund_payment_method_mapping.journal_id.id or shopify_instance_id.marketplace_refund_journal_id.id,
                        'amount': shopify_refund_amount,
                        'payment_date': tran_id.get('created_at') or fields.Datetime.now(),
                    }

                    payment_method_line_id = shopify_instance_id.marketplace_refund_journal_id.outbound_payment_method_line_ids.filtered(
                        lambda l: l.payment_method_id.id == shopify_instance_id.marketplace_outbound_method_id.id)
                    if payment_method_line_id:
                        wizard_vals['payment_method_line_id'] = payment_method_line_id.id

                    pmt_wizard = self.env['account.payment.register'].with_context(
                        active_model='account.move',
                        active_ids=refund_move_id.ids).create(wizard_vals)

                    payment = pmt_wizard._create_payments()
                    if len(payment) == 1:
                        payment.write({
                            'shopify_id': tran_shopify_id,
                            'marketplace_instance_id': shopify_instance_id.id,
                            'shopify_payment_gateway_names': tran_id.get('gateway'),
                        })
                    _logger.info("Refund payment created for Shopify transaction %s on order %s", tran_shopify_id, rec.name)
                    if refund_move_id.payment_state in ['paid', 'in_payment']:
                        rec.write({"shopify_is_refund": True})

        return move_id, message

    def get_order_fullfillments(self):
        for rec in self:
            marketplace_instance_id = rec.marketplace_instance_id
            if not getattr(marketplace_instance_id, "use_graphql", False):
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            order_data = rec._shopify_get_order_finance_graphql()
            fullfillment = {"fulfillments": order_data.get('fulfillments') or []}

            if fullfillment.get('errors'):
                self.message_post(body=_("Opps.. Error-{}".format(fullfillment.get('errors'))))
            else:
                _logger.info("\nSuccess---->")
                if rec.state not in ['cancel'] and fullfillment.get('fulfillments') and marketplace_instance_id.auto_create_fulfilment:
                    shopify_fulfil_obj = self.env['shopify.fulfilment']
                    for fulfillment in fullfillment.get('fulfillments'):
                        exist_fulfilment = shopify_fulfil_obj.search([("shopify_fulfilment_id", "=", fulfillment['id']),
                                                                      ("shopify_instance_id", "=",
                                                                       marketplace_instance_id.id),
                                                                      ("sale_order_id", "=", rec.id)], limit=1)

                        fulfillment_vals = {
                            "name": rec.name + '#' + str(fulfillment.get("order_id"))[:3],
                            "sale_order_id": rec.id,
                            "shopify_instance_id": marketplace_instance_id.id,
                            "shopify_order_id": fulfillment.get("order_id"),
                            "shopify_fulfilment_id": fulfillment.get("id"),
                            "shopify_fulfilment_tracking_number": fulfillment.get("tracking_number"),
                            "shopify_fulfilment_service": fulfillment.get("service"),
                            "shopify_fulfilment_status": fulfillment.get("line_items")[0].get("fulfillment_status"),
                            "shopify_status": fulfillment.get("status"),
                            "shopify_tracking_company": fulfillment.get("tracking_company"),
                            "shopify_shipment_status": fulfillment.get("shipment_status"),
                            "shopify_tracking_urls": ','.join(fulfillment.get("tracking_urls")),
                        }

                        fulfillment_line_vals = []
                        for line_item in fulfillment.get("line_items"):
                            fulfillment_line_vals += [(0, 0, {
                                "sale_order_id": rec.id,
                                "name": rec.name + ":" + line_item.get("name"),
                                "shopify_instance_id": marketplace_instance_id.id,
                                "shopify_fulfilment_line_id": line_item.get("id"),
                                "shopify_fulfilment_product_id": line_item.get("product_id"),
                                "shopify_fulfilment_product_variant_id": line_item.get("variant_id"),
                                "shopify_fulfilment_product_title": line_item.get("title"),
                                "shopify_fulfilment_product_name": line_item.get("name"),
                                "shopify_fulfilment_service": line_item.get("fulfillment_service"),
                                "shopify_fulfilment_qty": line_item.get("quantity"),
                                "shopify_fulfilment_grams": line_item.get("grams"),
                                "shopify_fulfilment_price": line_item.get("price"),
                                "shopify_fulfilment_total_discount": line_item.get("total_discount"),
                                "shopify_fulfilment_status": line_item.get("total_discount"),
                            })]
                        fulfillment_vals["shopify_fulfilment_line"] = fulfillment_line_vals
                        if exist_fulfilment:
                            shopify_fulfil_obj.update(fulfillment_vals)
                        else:
                            shopify_fulfil_obj.create(fulfillment_vals)
                    # if shopify_fulfil_obj:
                    #     try:
                    #         shopify_fulfil_obj._cr.commit()
                    #     except Exception as e:
                    #         _logger.warning("Exception - {}".format(e.args))

    def _shopify_get_order_finance_graphql(self):
        self.ensure_one()
        marketplace_instance_id = self.marketplace_instance_id
        query = """
        query SyncoriaOrderFinance($id: ID!) {
          order(id: $id) {
            transactions(first: 100) {
              amountSet { shopMoney { amount currencyCode } }
              id
              kind
              status
              gateway
              manualPaymentGateway
              processedAt
              receiptJson
            }
            refunds(first: 50) {
              id
              createdAt
              note
              orderAdjustments {
                kind
                reason
                amountSet { shopMoney { amount } }
              }
              transactions(first: 50) {
                edges {
                  node {
                    amountSet { shopMoney { amount currencyCode } }
                    id
                    kind
                    status
                    gateway
                    manualPaymentGateway
                    processedAt
                    receiptJson
                  }
                }
              }
              refundLineItems(first: 100) {
                edges {
                  node {
                    quantity
                    lineItem {
                      legacyResourceId
                      title
                      variant { legacyResourceId }
                      product { legacyResourceId }
                    }
                  }
              }
            }
          }
            fulfillments(first: 50) {
              legacyResourceId
              status
              shipmentStatus
              trackingCompany
              trackingInfo { number company url }
              lineItems(first: 250) {
                edges {
                  node {
                    quantity
                    lineItem {
                      legacyResourceId
                      title
                      variant { legacyResourceId }
                      product { legacyResourceId }
                    }
                }
              }
            }
          }
        }
        }
        """
        connector = self.env['marketplace.connector']
        res, _next = connector.shopify_graphql_call(
            headers={'X-Service-Key': marketplace_instance_id.token},
            url='/graphql.json',
            query=query,
            variables={"id": to_shopify_gid("Order", self.shopify_id)},
            type='POST',
            marketplace_instance_id=marketplace_instance_id,
        )
        if res.get('errors'):
            _logger.warning(
                "Shopify finance GraphQL query returned errors for order %s: %s",
                self.shopify_id,
                res.get('errors'),
            )
            # Fallback: at least fetch transactions so payments can still be synced.
            tx_query = """
            query SyncoriaOrderTransactionsOnly($id: ID!) {
              order(id: $id) {
                transactions(first: 100) {
                  amountSet { shopMoney { amount currencyCode } }
                  id
                  kind
                  status
                  gateway
                  manualPaymentGateway
                  processedAt
                  receiptJson
                }
              }
            }
            """
            tx_res, _next = connector.shopify_graphql_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url='/graphql.json',
                query=tx_query,
                variables={"id": to_shopify_gid("Order", self.shopify_id)},
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
            )
            if tx_res.get('errors'):
                _logger.warning(
                    "Shopify transactions-only fallback also failed for order %s: %s",
                    self.shopify_id,
                    tx_res.get('errors'),
                )
                return {"transactions": [], "refunds": [], "fulfillments": []}
            res = tx_res

        def _items(data):
            if not data:
                return []
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                if isinstance(data.get("nodes"), list):
                    return data.get("nodes") or []
                if isinstance(data.get("edges"), list):
                    return [e.get("node") for e in (data.get("edges") or []) if isinstance(e, dict) and e.get("node")]
                return [data]
            return []

        def _gid_num(v):
            if not v:
                return None
            s = str(v)
            if "/" in s:
                s = s.split("/")[-1]
            try:
                return int(s)
            except Exception:
                return None

        node = ((res.get("data") or {}).get("order") or {})
        transactions = []
        for tr in _items(node.get("transactions")):
            tr_kind = (tr.get("kind") or "").lower() or None
            tr_status = (tr.get("status") or "").lower() or None
            transactions.append({
                "id": _gid_num(tr.get("id")),
                "kind": tr_kind,
                "status": tr_status,
                "gateway": tr.get("gateway"),
                "manual_payment_gateway": tr.get("manualPaymentGateway"),
                "processed_at": tr.get("processedAt"),
                "amount": str(((tr.get("amountSet") or {}).get("shopMoney") or {}).get("amount")),
                "currency": (((tr.get("amountSet") or {}).get("shopMoney") or {}).get("currencyCode")),
                "receipt": tr.get("receiptJson"),
            })
        refunds = []
        for rf in _items(node.get("refunds")):
            r = {
                "id": _gid_num(rf.get("id")),
                "created_at": rf.get("createdAt"),
                "note": rf.get("note"),
                "order_adjustments": [],
                "transactions": [],
                "refund_line_items": [],
            }
            for oa in (rf.get("orderAdjustments") or []):
                r["order_adjustments"].append({
                    "kind": oa.get("kind"),
                    "reason": oa.get("reason"),
                    "amount": str(((oa.get("amountSet") or {}).get("shopMoney") or {}).get("amount")),
                })
            for rt in _items(rf.get("transactions")):
                rt_kind = (rt.get("kind") or "").lower() or None
                rt_status = (rt.get("status") or "").lower() or None
                r["transactions"].append({
                    "id": _gid_num(rt.get("id")),
                    "kind": rt_kind,
                    "status": rt_status,
                    "gateway": rt.get("gateway"),
                    "manual_payment_gateway": rt.get("manualPaymentGateway"),
                    "processed_at": rt.get("processedAt"),
                    "amount": str(((rt.get("amountSet") or {}).get("shopMoney") or {}).get("amount")),
                    "currency": (((rt.get("amountSet") or {}).get("shopMoney") or {}).get("currencyCode")),
                    "receipt": rt.get("receiptJson"),
                })
            for rli in _items(rf.get("refundLineItems")):
                li = rli.get("lineItem") or {}
                r["refund_line_items"].append({
                    "quantity": rli.get("quantity"),
                    "line_item": {
                        "id": _gid_num(li.get("legacyResourceId")),
                        "title": li.get("title"),
                        "variant_id": _gid_num((li.get("variant") or {}).get("legacyResourceId")),
                        "product_id": _gid_num((li.get("product") or {}).get("legacyResourceId")),
                    }
                })
            refunds.append(r)
        fulfillments = []
        for ff in _items(node.get("fulfillments")):
            tracking = (ff.get("trackingInfo") or [{}])[0] or {}
            fulfillments.append({
                "id": _gid_num(ff.get("legacyResourceId")),
                "order_id": int(self.shopify_id or 0),
                "tracking_number": tracking.get("number"),
                "service": tracking.get("company"),
                "status": ff.get("status"),
                "tracking_company": ff.get("trackingCompany"),
                "shipment_status": ff.get("shipmentStatus"),
                "tracking_urls": [tracking.get("url")] if tracking.get("url") else [],
                "line_items": [{
                    "id": _gid_num((ln.get("lineItem") or {}).get("legacyResourceId")) or 0,
                    "line_item_id": _gid_num((ln.get("lineItem") or {}).get("legacyResourceId")) or 0,
                    "product_id": _gid_num(((ln.get("lineItem") or {}).get("product") or {}).get("legacyResourceId")) or 0,
                    "variant_id": _gid_num(((ln.get("lineItem") or {}).get("variant") or {}).get("legacyResourceId")) or 0,
                    "title": (ln.get("lineItem") or {}).get("title"),
                    "name": (ln.get("lineItem") or {}).get("title"),
                    "fulfillment_service": tracking.get("company"),
                    "quantity": ln.get("quantity"),
                    "grams": 0,
                    "price": "0.0",
                    "total_discount": "0.0",
                    "fulfillment_status": ff.get("status"),
                } for ln in _items(ff.get("lineItems"))],
            })

        # Prefer REST payloads when available: Odoo transaction/fulfillment tables expect REST fields
        # like message/test/authorization/source_name/location_id and full fulfillment line item details.
        try:
            rest_tx, _next = connector.shopify_api_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url="/orders/%s/transactions.json" % self.shopify_id,
                type="GET",
                marketplace_instance_id=marketplace_instance_id,
            )
            if isinstance(rest_tx, dict) and isinstance(rest_tx.get("transactions"), list):
                transactions = rest_tx.get("transactions") or []
        except Exception as e:
            _logger.warning("REST transactions fetch failed for order %s: %s", self.shopify_id, e)

        try:
            rest_rf, _next = connector.shopify_api_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url="/orders/%s/refunds.json" % self.shopify_id,
                type="GET",
                marketplace_instance_id=marketplace_instance_id,
            )
            if isinstance(rest_rf, dict) and isinstance(rest_rf.get("refunds"), list):
                refunds = rest_rf.get("refunds") or []
        except Exception as e:
            _logger.warning("REST refunds fetch failed for order %s: %s", self.shopify_id, e)

        try:
            rest_ff, _next = connector.shopify_api_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url="/orders/%s/fulfillments.json" % self.shopify_id,
                type="GET",
                marketplace_instance_id=marketplace_instance_id,
            )
            if isinstance(rest_ff, dict) and isinstance(rest_ff.get("fulfillments"), list):
                fulfillments = rest_ff.get("fulfillments") or []
        except Exception as e:
            _logger.warning("REST fulfillments fetch failed for order %s: %s", self.shopify_id, e)

        return {"transactions": transactions, "refunds": refunds, "fulfillments": fulfillments}

    def process_shopify_fulfilment(self):
        for rec in self:
            success_fulfilment = rec.shopify_fulfilment_ids.filtered(lambda l: l.shopify_status == 'success')
            if success_fulfilment:
                for fulfilment in success_fulfilment:
                    picking_exist = rec.picking_ids.filtered_domain([('shopify_id', "=", fulfilment.shopify_fulfilment_id), ('state', '!=', 'done')])
                    try:
                        if not picking_exist:
                            if rec.delivery_count == 1 and not rec.picking_ids.shopify_id:
                                self._process_picking(fulfilment, rec.picking_ids, rec)
                            else:
                                backorder_picking = rec.picking_ids.filtered_domain(
                                    [('backorder_id', "!=", False), ('state', '!=', 'done')])
                                self._process_picking(fulfilment, backorder_picking, rec)
                        else:
                            if picking_exist.state != 'done':
                                self._process_picking(fulfilment, picking_exist, rec)
                    except Exception as e:
                        rec.message_post(body="Exception-Order#{}-{}".format(rec.id, e.args))

    def _process_picking(self, fulfilment, picking, order):
        flag = False
        for fulfilment_item in fulfilment.shopify_fulfilment_line:
            stock_move_id = picking.move_ids.filtered(lambda m: m.sale_line_id.shopify_id == fulfilment_item.shopify_fulfilment_line_id)
            if stock_move_id:
                flag = True
                stock_move_id.write({'quantity': fulfilment_item.shopify_fulfilment_qty})
        # delivery_products = self.env['delivery.carrier'].search([]).product_id
        # delivery_lines = picking.move_lines.filtered(lambda m: m.product_id in delivery_products)
        # if delivery_lines:
        #     delivery_lines.write({'quantity_done': 1})
        if flag:
            picking.shopify_id = fulfilment.shopify_fulfilment_id
            picking.carrier_tracking_ref = fulfilment.shopify_fulfilment_tracking_number
            picking.shopify_tracking_company = fulfilment.shopify_tracking_company
            picking.shopify_tracking_urls = fulfilment.shopify_tracking_urls
            picking.marketplace_instance_id = order.marketplace_instance_id.id
            picking.shopify_status = fulfilment.shopify_shipment_status
            picking.shopify_service = fulfilment.shopify_fulfilment_service
            picking.shopify_tracking_number = fulfilment.shopify_fulfilment_tracking_number

            picking.action_confirm()
            picking.action_assign()
            validate_picking = picking.button_validate()
            if type(validate_picking) != bool:
                validate_picking = self.env['stock.backorder.confirmation'].with_context(validate_picking.get('context')).process()

    def _prepare_confirmation_values(self):
        res = super(SaleOrderShopify, self)._prepare_confirmation_values()
        for order in self:
            if order.marketplace_type == 'shopify':
                ctx = self.env.context
                return {
                    'state': 'sale',
                    'date_order': ctx.get('date_order') if ctx.get('date_order') else fields.Datetime.now()
                }
        return res

    def _prepare_invoice(self):
        res = super(SaleOrderShopify, self)._prepare_invoice()
        for order in self:
            if order.marketplace_type == 'shopify':
                res['invoice_date'] = self.date_order

        return res

    def _get_invoiceable_lines(self, final=False):
        lines = super()._get_invoiceable_lines(final=final)

        for order in self:
            if not order.marketplace_type == 'shopify':
                continue

            shopify_lines = order.order_line.filtered(
                lambda l:
                l.product_id.invoice_policy == 'delivery'
                and l.qty_delivered == 0
                and l.product_uom_qty > 0
            )

            lines |= shopify_lines

        return lines


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    shopify_id = fields.Char(string="Shopify Id", readonly=True, store=True)
    line_coupon_ids = fields.Many2many('shopify.coupon', string="Shopify Coupons Line")

    @api.depends(
        'qty_delivered',
        'qty_invoiced',
        'product_uom_qty',
        'order_id.state',
        'order_id.marketplace_type',
    )
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()

        for line in self:
            if (
                    line.order_id.marketplace_type == 'shopify'
                    and line.product_id.invoice_policy == 'delivery'
            ):
                line.qty_to_invoice = (
                        line.product_uom_qty - line.qty_invoiced
                )
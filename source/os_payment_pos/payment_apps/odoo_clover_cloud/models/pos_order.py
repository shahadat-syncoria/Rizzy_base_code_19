# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
import requests

import logging
_logger = logging.getLogger(__name__)


class PosOrderInherit(models.Model):
    _inherit = 'pos.order'

    clover_request_id = fields.Char("Clover Request ID")
    clover_ext_payment_ids = fields.Char("Clover External Payment Ids")
    clover_last_action = fields.Char("Clover Last Action")

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrderInherit, self)._order_fields(ui_order)
        if "clover_request_id" in ui_order:
            order_fields['clover_request_id'] = ui_order["clover_request_id"]

        return order_fields
    @api.model
    def _payment_fields(self, order,  ui_paymentline):
        _logger.info("ui_paymentline")
        _logger.info(ui_paymentline)

        fields = super(PosOrderInherit, self)._payment_fields(
            order,  ui_paymentline)

        PaymentMethod = self.env['pos.payment.method']
        if fields.get('payment_method_id'):
            method_id = PaymentMethod.sudo().search(
                [('id', '=', fields.get('payment_method_id'))])
            if method_id.use_payment_terminal == 'clover_cloud':
                # Update Order clover_ext_payment_ids
                ext_payment_ids = order.clover_ext_payment_ids + "," + ui_paymentline.get(
                    'clover_payment_id') if order.clover_ext_payment_ids else ui_paymentline.get('clover_payment_id')
                try:
                    order.write({'clover_ext_payment_ids': ext_payment_ids})
                except Exception as e:
                    _logger.warning("order.write-->" + str(e.args))

                # Update Clover Payment
                try:
                    if ui_paymentline.get('clover_success') and ui_paymentline.get('clover_result'):
                        clover_pay = self.env['clover.payment']
                        clover_pay.sudo().search([('order_name', '=', order.pos_reference), (
                            'external_pay_id', '=', ui_paymentline.get('clover_order_id'))], order='id desc', limit=1)
                        if clover_pay:
                            clover_pay[0].write({'payment_status':ui_paymentline.get('clover_payment_result')})
                except Exception as e:
                    _logger.warning("Update Clover Payment Failed: " + str(e.args))


                fields.update({
                    'clover_request_id': ui_paymentline.get('clover_request_id',''),
                    'clover_success': ui_paymentline.get('clover_success',''),
                    'clover_result': ui_paymentline.get('clover_result',''),
                    'clover_payment_id': ui_paymentline.get('clover_payment_id',''),
                    'clover_order_id':  ui_paymentline.get('clover_order_id',''),
                    'clover_tender_id': ui_paymentline.get('clover_tender_id',''),
                    'clover_amount': ui_paymentline.get('clover_amount',''),
                    'clover_ext_id': ui_paymentline.get('clover_ext_id',''),
                    'clover_emp_id': ui_paymentline.get('clover_emp_id',''),
                    'clover_created_time': ui_paymentline.get('clover_created_time',''),
                    'clover_payment_result': ui_paymentline.get('clover_payment_result',''),
                    'clover_entry_type': ui_paymentline.get('clover_entry_type',''),
                    'clover_type': ui_paymentline.get('clover_type',''),
                    'clover_auth_code': ui_paymentline.get('clover_auth_code',''),
                    'clover_reference_id': ui_paymentline.get('clover_reference_id',''),
                    'clover_transaction_no': ui_paymentline.get('clover_transaction_no',''),
                    'clover_state': ui_paymentline.get('clover_state',''),
                    'clover_last_digits': ui_paymentline.get('clover_last_digits',''),
                    'clover_expiry_date': ui_paymentline.get('clover_expiry_date',''),
                    'clover_token': ui_paymentline.get('clover_token',''),
                    # Basic Odoo Fields
                    'card_type': ui_paymentline.get('card_type',''),
                    'cardholder_name':  ui_paymentline.get('cardholder_name',''),
                    'transaction_id': ui_paymentline.get('clover_transaction_no',''),
                    # Refund Fields
                    'clover_refund_reason': ui_paymentline.get('clover_refund_reason',''),
                    'clover_message': ui_paymentline.get('clover_message',''),
                    'clover_refund_id': ui_paymentline.get('clover_refund_id',''),
                    'clover_refund_device_id': ui_paymentline.get('clover_refund_device_id',''),
                    'clover_tax_amount': ui_paymentline.get('clover_tax_amount',''),
                    'clover_client_created_time': ui_paymentline.get('clover_client_created_time',''),
                    'clover_voided': ui_paymentline.get('clover_voided',''),
                    'clover_transaction_info': ui_paymentline.get('clover_transaction_info',''),

                })

        return fields

    def add_payment(self, data):
        """Create a new payment for the order"""
        values = super(PosOrderInherit, self).add_payment(data)
        write_values = {}
        field_values = []

        payments = self.payment_ids

        if len(payments) > 0:
            if payments[0].payment_method_id.use_payment_terminal == 'clover_clover':
                for key, value in payments[0]._fields.items():
                    field_values.append(key)

                for key, value in data.items():
                    if key in field_values:
                        write_values[key] = value

                if (data.get('clover_card_type') or data.get('card_type')) and not write_values.get('clover_card_type'):
                    write_values['clover_card_type'] = data.get('card_type')
                print("write_values")
                print(write_values)
                payments[0].write(write_values)
        return values

    def insert_logging(self, kwargs):
        try:
            Log = self.env['ir.logging']
            Log.create({
                'func': 'Clover Log',
                'level': kwargs.get('level') or '',
                'line': kwargs.get('line') or '',
                'message': kwargs.get('message') or '',
                'name': kwargs.get('name') or '',
                'path': kwargs.get('path') or '',
                'type': kwargs.get('type') or 'client',
            })
        except Exception as e:
            _logger.warning("Insert Logging Erorr-------->" + str(e.args))

    def save_external_id(self, kwargs):
        for record in self:
            record.write({'clover_ext_payment_ids': ''})

    def get_clover_payments(self, kwargs):
        try:
            if kwargs.get('payment_method_id') and kwargs.get('externalPaymentId'):
                PayMtd = self.env['pos.payment.method']
                paymtd_id = PayMtd.sudo().browse(int(kwargs.get('payment_method_id')))
                URL = "{base_url}/v3/merchants/{merchantId}/payments?filter=externalPaymentId={externalPaymentId}"
                URL.replace('base_url', paymtd_id.clover_server_url)
                URL.replace('merchantId', paymtd_id.clover_merchant_id)
                URL.replace('externalPaymentId',
                            kwargs.get('externalPaymentId'))

                res = requests.get(URL)
                if res.status_code == 200:
                    _logger.info("Successful Connection")
                else:
                    _logger.warning(res.status_code)
            else:
                _logger.warning(
                    "Either Payment Method or externalPaymentId not found!")
        except Exception as e:
            _logger.warning("get_clover_payments Error" + str(e.args))


    def get_clover_payments(self, kwargs):
        print("get_clover_payments")
        res= {}
        name = self.id
        self = self.env['pos.order'].sudo().search([('pos_reference','=',name)])
        if self:
            AccPayments = self.env['account.payment']
            payments =  AccPayments.sudo().search([('pos_order_id','=',self.id)])
            if len(payments) == 1:
                res = {
                    'clover_order_id' : payments.clover_order_id,
                    'clover_payment_id' : payments.clover_payment_id,
                }
        return res
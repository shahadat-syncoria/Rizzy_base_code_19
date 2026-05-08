# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api
from odoo.service import common
import pprint
import logging
_logger = logging.getLogger(__name__)

version_info = common.exp_version()
server_serie = version_info.get('server_serie') 

class PosPaymentInherit(models.Model):
    _inherit = 'pos.payment'

    clover_request_id = fields.Char(string='Request Id',)
    
    clover_success = fields.Char(string='Success',)
    clover_result = fields.Char(string='Result',)
    clover_payment_id = fields.Char(string='Payment Id',)
    clover_order_id = fields.Char(string='Order Id',)
    clover_tender_id = fields.Char(string='Tender Id',)
    clover_amount = fields.Char(string='Clover Amt.',)
    clover_ext_id = fields.Char(string='External Payment Id',)
    clover_emp_id = fields.Char(string='Employee Id',)
    clover_created_time = fields.Char(string='Created Time',)
    clover_payment_result = fields.Char(string='Payment Result',)
    
    clover_entry_type = fields.Char(string='Entry Type',)
    clover_type = fields.Char(string='Clover Type',)
    clover_auth_code = fields.Char(string='Auth Code',)
    clover_reference_id = fields.Char(string='Reference Id',)
    clover_transaction_no = fields.Char(string='Transaction No',)
    clover_state = fields.Char(string='State',)
    clover_last_digits = fields.Char(string='Last 4 digits',)
    clover_expiry_date = fields.Char(string='Expiry Date',)
    clover_token = fields.Char(string='Token',)
    clover_device_id = fields.Char(string='Device Id',)
    # Refund Parts
    clover_refund_device_id = fields.Char(string='Refund Device Id',)
    clover_refund_reason = fields.Char(string='Reason',)
    clover_message = fields.Char(string='Message',)
    clover_refund_id = fields.Char(string='Refund Id',)
    clover_tax_amount = fields.Char(string='Tax Amt.',)
    clover_client_created_time = fields.Char(string='Client Created Time',)
    clover_voided = fields.Char(string='Voided',)
    clover_transaction_info = fields.Char(string='Transaction Info',)

    is_clover_payment = fields.Boolean(
        default=False,
        compute='compute_is_clover_payment')

    
    @api.depends('payment_method_id')
    def compute_is_clover_payment(self):
        for record in self:
            record.is_clover_payment = False
            if record.payment_method_id.use_payment_terminal == 'clover_cloud':
                record.is_clover_payment = True
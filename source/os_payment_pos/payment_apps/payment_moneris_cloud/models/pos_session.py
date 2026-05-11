# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models,api


class MonerisCloudPosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields']+=['cloud_store_id', 'cloud_api_token', 'cloud_terminal_id','is_moneris_go_cloud',
        'cloud_postback_url', 'cloud_cloud_environment', 'cloud_integration_method','cloud_inout_url', 'cloud_out_url1', 'cloud_out_url2', 'token', 'company_id']
        return result

    def _loader_params_pos_order(self):
        result = super()._loader_params_pos_order()
        result['search_params']['fields']+=['moneris_cloud_cloudticket','moneris_cloud_receiptid','moneris_cloud_transid']
        return result
    def _loader_params_pos_payment(self):
        result = super()._loader_params_pos_payment()
        result['search_params']['fields']+=['cloud_receipt_customer','cloud_receipt_merchant']
        return result

    @api.model
    def _load_pos_data_models(self, config_id):
        return super()._load_pos_data_models(config_id)+['moneris.pos.preauth']


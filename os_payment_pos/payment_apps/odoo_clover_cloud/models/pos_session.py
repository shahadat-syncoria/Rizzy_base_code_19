# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class CloverCloudPosSession(models.Model):
    _inherit = 'pos.session'

    # def _pos_ui_models_to_load(self):
    #     result = super()._pos_ui_models_to_load()
    #     result.append('pos.order')
    #     return result

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        result['search_params']['fields']+=[ 'clover_server_url',
        'clover_config_id',
        'clover_jwt_token',
        'clover_device_id',
        'clover_device_name',
        'clover_x_pos_id',]
        return result

    # ======================== POS ORDER ===================
    # def _pos_data_process(self, loaded_data):
    #     super()._pos_data_process(loaded_data)
    #     if len(loaded_data['iot.device']) > 0:
    #         loaded_data['pos.config']['use_proxy'] = True

    def _loader_params_pos_order(self):
        result = super()._loader_params_pos_order()
        result['search_params']['fields']+= ['name', 'session_id', 'date_order', 'pos_reference', 'partner_id', 'user_id', 'amount_total',
                     'pos_order_date',
                     'clover_request_id',
                    'clover_ext_payment_ids',
                    'clover_last_action',
                     'payment_ids',
                     ]
        return result



# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import requests
import json

_logger = logging.getLogger(__name__)



class CloverDevice(models.Model):
    _name = 'clover.device'
    _description = 'Clover Device'
    _rec_name = 'name'

    name = fields.Char(default='New Clover Device')
    device_id = fields.Char('Device Id')   
    model = fields.Char()  
    serial = fields.Char()
    secure_id = fields.Char('Secure Id') 
    build_type = fields.Char() 
    device_type_name = fields.Char() 
    product_name = fields.Char() 
    pin_disabled = fields.Boolean() 
    offline_payments = fields.Boolean() 
    offline_payments_all = fields.Boolean() 
    device_status = fields.Boolean()
    x_pos_id = fields.Char()
    is_sale = fields.Boolean(string='Sale Device', default=True)
    # method_id = fields.Many2one(
    #     string='Payment Method Id',
    #     comodel_name='pos.payment.method',
    #     ondelete='restrict',
    #     domain=[('use_payment_terminal','=','clover_cloud')],
    # )
    journal_id = fields.Many2one(
        string='Journal Id',
        comodel_name='account.journal',
        ondelete='restrict',
        domain=[('use_clover_terminal','=',True)],
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = vals.get('serial') or vals.get('device_id') or 'New Clover Device'
        return super().create(vals_list)

    def action_ping_device(self):
        """action_ping_device"""
        if not self.serial or not self.x_pos_id:
            raise UserError(_("Please provide device serial and POS ID..."))

        try:
            URL = '%s/api/v1/device/connect' % (self.journal_id.clover_server_url)
            headers = {
                "Authorization": "Bearer %s" %(self.journal_id.clover_jwt_token), 
                "Content-Type": "application/json",
                "X-Clover-Device-Id": self.serial,
                "X-POS-Id": self.x_pos_id,
            }
            payload = {
                "configId": self.journal_id.clover_config_id,
                "deviceId": self.serial,
                "posId": self.x_pos_id
            }
            response = requests.post(url=URL, headers=headers,data=json.dumps(payload))
            device_status = False
            if response.status_code == 200:
                res_json = response.json()
                if not res_json.get('message', {}).get('error'):
                    device_status = True
            self.device_status = device_status
            status = "Not Reachable" if device_status == False else "Reachable"

            message = _("Deviced Status for {}: {}".format(self.serial, status))
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message,
                    'type': 'success',
                    'sticky': False,
                }
            }


        except Exception as e:
            raise UserError(_("Exception: {}".format(e.args)))
            

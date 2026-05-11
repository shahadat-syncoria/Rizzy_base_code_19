# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import json
import requests

_logger = logging.getLogger(__name__)

test_url = 'https://sandbox.dev.clover.com'
prod_url = 'https://www.clover.com'
regions = {
    'uscanada': 'https://www.clover.com',
    'europe': 'https://eu.clover.com',
}


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('clover_cloud', 'Clover Cloud')]
    def _get_device(self,**kwargs):
        a=1
        return [('method_id', '=', self.id)]
    clover_server_url = fields.Char(string='Clover Server URL',)
    clover_config_id = fields.Char(string='Clover Config Id',)
    clover_jwt_token = fields.Text(string='Clover JWT Token',)
    clover_merchant_id = fields.Char(string='Clover Merchant Id')
    clover_device_id = fields.Many2one(
        string='Device',
        comodel_name='clover.device',
        ondelete='restrict',
        # domain=lambda self: self._get_device(),
        help="To obtain the deviceId, you must first retrieve an accessToken and your merchantId. Press 'Get Device Id' button to get the Device Id."
    )
    clover_device_name = fields.Char(
        string='Device ID',
        compute='_compute_clover_device_name')

    @api.depends('clover_device_id')
    def _compute_clover_device_name(self):
        for record in self:
            record.clover_device_name = record.clover_device_id.serial

    clover_x_pos_id = fields.Char(
        string='X POS ID',
        compute='_compute_clover_x_pos_id')

    @api.depends('clover_device_id')
    def _compute_clover_x_pos_id(self):
        for record in self:
            record.clover_x_pos_id = ""
            if record.clover_device_id:
                record.clover_x_pos_id = record.clover_device_id.x_pos_id

    # Clover Log
    clover_log_ids = fields.One2many(
        string='Clover Logs',
        comodel_name='ir.logging',
        inverse_name='payment_method_id',
        domain=[('payment_method_id', '!=', False), ((
            'payment_method_id.use_payment_terminal', '=', 'clover_cloud'))]
    )


    # =========================================  Odoo 18 Payment Method Data load to POS ========================================
    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['clover_server_url','clover_config_id','clover_jwt_token','clover_device_id','clover_device_name','clover_x_pos_id']
        return params

    # ===========================================================================================================================
    def fetch_clover_device(self):
        """Button to get the device id using the CLover Merchant Id(App Id) and the Clover
            Access Token."""
        _logger.info("fetch_clover_device")

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            raise UserError(_("Please provide both Config Id and JWT Token."))

    
        try:    
            CloverDevice = self.env['clover.device'].sudo()
            device_ids = []
            URL = '%s/api/device/get-all' % (self.clover_server_url)
            headers = {"Authorization": "Bearer %s" % (self.clover_jwt_token)}
            response = requests.get(url=URL, headers=headers)


            _logger.info("URL ===>>>>{}".format(URL))
            _logger.info("headers ===>>>>{}".format(headers))
            _logger.info("Response-->" + str(response.text))

            if response.status_code == 200:
                res_json = response.json()
                elem_len = 0
                if res_json:
                    i = 0
                    for device in res_json:
                        device_ids.append(device.get("id"))
                        dev_srch = CloverDevice.search(
                            [('serial', '=', device.get("serial"))])
                        if(len(dev_srch) == 0):
                            CloverDevice.create({
                                'serial': device.get("serial"),
                                'device_id': device.get("id"),
                                'method_id': self.id,
                                'model': device.get("model"),
                                'secure_id': device.get("secureId"),
                                'build_type': device.get("buildType"),
                                'device_type_name': device.get("deviceTypeName"),
                                'product_name': device.get("productName"),
                                'pin_disabled': device.get("pinDisabled"),
                                'offline_payments': device.get("offlinePayments"),
                                'offline_payments_all': device.get("offlinePaymentsAll"),
                                'x_pos_id': self.name,
                            })
                            i += 1

                    # Logging Informations
                    elem_len = len(res_json)
                    message = "Number of Devices Fetched %d" % (elem_len) + "\n, Devices Ids: " + str(device_ids)
                    log_vals = {
                        "func": "update_webhook_code",
                        "line": "35",
                        "message": message,
                        "name": "CloverWebhookUrl",
                        "path": "/clover/webhook/",
                        "type": "server",
                        "level": "info",
                        "journal_id": self.id,
                    }
                    self.create_logging(log_vals)
                    self._cr.commit()
                message = _("Deviced Fetched: %d" % (elem_len))
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': message,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                message = ''
                for key, value in response.json().items():
                    message += str(key) + ": " + response.json()[key]
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
            raise UserError(_("Sorry.. Can not connect to Server. Please try again after sometime."))

    def get_clover_fields(self, kwargs):
        _logger.info("get_clover_fields")
        _logger.info("kwargs" + str(kwargs))

        self = self.search([('id', '=', int(kwargs.get('id')))])
        result = {}
        result['clover_application_id'] = self.clover_application_id
        result['clover_merchant_id'] = self.clover_merchant_id
        result['clover_access_token'] = self.clover_access_token
        result['clover_device_id'] = self.clover_device_id.device_id
        result['clover_server'] = self.clover_server
        result['clover_friendly_id'] = self.clover_friendly_id
        result['state'] = self.state
        result['clover_region'] = self.clover_region
        result['clover_cloud_paired'] = self.clover_cloud_paired
        return result

    def create_logging(self, log_vals):
        _logger.info("create_logging")
        IrLog = self.env['ir.logging'].sudo()
        IrLog.create(log_vals)

    def get_headers(self, values):
        return {
            "Authorization": "Bearer %s" % (self.clover_jwt_token),
            "Content-Type": "application/json",
            "X-Clover-Device-Id": self.x_clover_device_id,
            "X-POS-Id": self.x_pos_id,
        }

        
    # def send_welcome_message(self, values):
    #     if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
    #         return {'success':False, 'description':'Config id or JWT Token or Server URL is missing'}

    #     URL = '%s/api/v1/show/welcome' % (self.clover_server_url)
    #     headers = self.get_headers(values)
    #     payload = {
    #         "configId": values.get('configId'),
    #         "deviceId": values.get('deviceId'),
    #         "posId": values.get('posId'),
    #     }

    #     response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

    #     _logger.info("URL ===>>>>{}".format(URL))
    #     _logger.info("headers ===>>>>{}".format(headers))
    #     _logger.info("payload ===>>>>{}".format(payload))
    #     _logger.info("response===>>>>" + str(response.text))

    #     if response.status_code == 200:
    #         return {
    #             'status_code' : response.status_code,
    #             'success': True,
    #             'description': 'Welcome Message sent Successfully',
    #             'action': 'welcome_message',
    #         }
    #     else:
    #         return {
    #             'status_code' : response.status_code,
    #             'success': False,
    #             'description': 'Welcome Message send failed!',
    #             'action': 'welcome_message',
    #         }

    # def send_thankyou_message(self, values):
    #     if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
    #         return {'success':False, 'description':'Config id or JWT Token or Server URL is missing'}

    #     URL = '%s/api/v1/show/thank-you' % (self.clover_server_url)
    #     headers = self.get_headers(values)
    #     payload = {
    #         "configId": values.get('configId'),
    #         "deviceId": values.get('deviceId'),
    #         "posId": values.get('posId'),
    #     }

    #     response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

    #     _logger.info("URL ===>>>>{}".format(URL))
    #     _logger.info("headers ===>>>>{}".format(headers))
    #     _logger.info("payload ===>>>>{}".format(payload))
    #     _logger.info("response===>>>>" + str(response.text))

    #     if response.status_code == 200:
    #         return {
    #             'success': True,
    #             'description': 'Thankyou Message sent Successfully',
    #             'action': 'thankyou_message',
    #         }
    #     else:
    #         return {
    #             'success': False,
    #             'description': 'Thankyou Message send failed!',
    #             'action': 'thankyou_message',
    #         }

    # def send_payment_receipt(self, values):
    #     if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
    #         return {'success':False, 'description':'Config id or JWT Token or Server URL is missing'}

    #     URL = '%s/api/v1/payments/%s/receipt/' % (self.clover_server_url, values.get('paymetId'))
    #     headers = self.get_headers(values)
    #     payload = {
    #         "configId": values.get('configId'),
    #         "deviceId": values.get('deviceId'),
    #         "posId": values.get('posId'),
    #     }

    #     response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

    #     _logger.info("URL ===>>>>{}".format(URL))
    #     _logger.info("headers ===>>>>{}".format(headers))
    #     _logger.info("payload ===>>>>{}".format(payload))
    #     _logger.info("response===>>>>" + str(response.text))

    #     if response.status_code == 200:
    #         return {
    #             'success': True,
    #             'description': 'Thankyou Message sent Successfully',
    #             'action': 'thankyou_message',
    #         }
    #     else:
    #         return {
    #             'success': False,
    #             'description': 'Thankyou Message send failed!',
    #             'action': 'thankyou_message',
    #         }

    # def send_payment_request(self, values):
    #     if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
    #         return {'success':False, 'description':'Config id or JWT Token or Server URL is missing'}

    #     URL = '%s/api/v1/payments/%s/receipt/' % (self.clover_server_url, values.get('paymetId'))
    #     headers = self.get_headers(values)
    #     payload = {
    #         "configId": values.get('configId'),
    #         "deviceId": values.get('deviceId'),
    #         "posId": values.get('posId'),
    #     }

    #     response = requests.request("POST", URL, headers=headers, data=json.dumps(payload))

    #     _logger.info("URL ===>>>>{}".format(URL))
    #     _logger.info("headers ===>>>>{}".format(headers))
    #     _logger.info("payload ===>>>>{}".format(payload))
    #     _logger.info("response===>>>>" + str(response.text))

    #     if response.status_code == 200:
    #         return {
    #             'success': True,
    #             'description': 'Thankyou Message sent Successfully',
    #             'action': 'thankyou_message',
    #         }
    #     else:
    #         return {
    #             'success': False,
    #             'description': 'Thankyou Message send failed!',
    #             'action': 'thankyou_message',
    #         }


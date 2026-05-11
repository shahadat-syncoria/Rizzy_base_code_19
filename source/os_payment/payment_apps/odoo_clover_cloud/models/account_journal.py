# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import requests

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    use_clover_terminal = fields.Boolean()
    clover_server_url = fields.Char()
    clover_config_id = fields.Char('Clover Config Id',)
    clover_jwt_token = fields.Text()
    clover_merchant_id = fields.Char()
    clover_device_id = fields.Many2one(
        string='Device',
        comodel_name='clover.device',
        ondelete='restrict',
        domain=lambda self: [('journal_id', '=', self.id)],
        help="To obtain the deviceId, you must first retrieve an accessToken and your merchantId. Press 'Get Device Id' button to get the Device Id."
    )
    clover_device_name = fields.Char(
        string='Device ID', 
        related='clover_device_id.device_id' )
    clover_log_ids = fields.One2many(
        string='Clover Logs',
        comodel_name='ir.logging',
        inverse_name='journal_id',
        domain=[('journal_id', '!=', False), (('journal_id.use_clover_terminal', '=', True))]
    )


    def fetch_clover_device(self):
        """Button to get the device id using the Clover Merchant Id(App Id) and the Clover
            Access Token."""
        _logger.info("fetch_clover_device")

        if not self.clover_config_id or not self.clover_jwt_token or not self.clover_server_url:
            raise UserError(_("Please provide both Config Id and JWT Token."))

        try:
            CloverDevice = self.env['clover.device'].sudo()
            device_ids = []
            URL = '%s/api/device/get-all' % (self.clover_server_url)
            headers = {"Authorization": "Bearer %s" %(self.clover_jwt_token) }
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
                        dev_srch = CloverDevice.search([('serial', '=', device.get("serial")), ('journal_id', '=', self.id)])
                        if(len(dev_srch) == 0):
                            CloverDevice.create({
                                'device_id': device.get("deviceId"),
                                'serial': device.get("serial"),
                                'journal_id' : self.id,
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
                    message = "Number of Devices Fetched %d" %(elem_len) + "\n, Devices Ids: " +str(device_ids)
                    log_vals = {
                        "func" : "update_webhook_code",
                        "line" : "35",
                        "message" : message,
                        "name" : "CloverWebhookUrl",
                        "path" : "/clover/webhook/",
                        "type" : "server",
                        "level" : "info",
                        "journal_id" : self.id,
                    }
                    self.create_logging(log_vals)
                    self._cr.commit()
                
                message = _("Deviced Fetched: %d" %(elem_len))
                if elem_len:
                    self.message_post(body=message)
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
                msgs = ''
                for key, value in response.json().items():
                    msgs += str(key) + ": " + response.json()[key]
                raise UserError(_("Error: \n " + str(msgs)))


        except Exception as e:
            raise UserError(_("Sorry.. Can not connect to Server. Please try again after sometime."))

    def get_clover_fields(self, kwargs):
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
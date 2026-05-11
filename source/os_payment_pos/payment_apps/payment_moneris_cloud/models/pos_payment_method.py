# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, exceptions, _
import logging
import json
import requests
from pprint import pprint
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('moneris_cloud', 'Moneris Cloud')]


    cloud_store_id = fields.Char(
        "Moneris Store ID", help="Unique identifier provided by Moneris upon merchant account setup", )
    cloud_api_token = fields.Char(
        "Moneris API Token", help="Unique alphanumeric string assigned by Moneris upon merchant account activation",)

    cloud_pairing_token = fields.Char(
        "Moneris Pairing Token", help="The ECR number of the particular PINpad you are addressing",)
    cloud_postback_url = fields.Char(
        "Moneris Postback URL", help="Value provided by the terminal as part of the pairing process")
    # cloud_polling = fields.Boolean("Moneris Polling",default=True)
    cloud_integration_method = fields.Selection([
        ('postbackurl', 'Postback URL'),
        ('polling', 'Cloud HTTPS Polling'),
        ('combined', 'Combined')],
        required=True, default='polling', copy=False, store=True, readonly=True)
    cloud_cloud_environment = fields.Selection([
        ('enabled', 'Enabled'),
        ('test', 'Test Mode')], string="Moneris Cloud Environment", default='test', copy=False, store=True)
    cloud_cloud_paired = fields.Boolean("Moneris Cloud Paired", default=False)
    cloud_cloud_ticket = fields.Boolean("Moneris Cloud Ticket", default=False)

    cloud_inout_url = fields.Char("cloud_inout_url", store=True)
    cloud_out_url1 = fields.Char("cloud_out_url1", store=True)
    cloud_out_url2 = fields.Char("cloud_out_url2", store=True)
 
    cloud_merchant_id = fields.Char()

    moneris_is_manual_payment = fields.Boolean(string="Is Manual Payment?", default=False)

    moneris_device_id = fields.Many2one("moneris.device", ondelete='restrict',
                                        domain=lambda self: [('journal_id', '=', self.id)], )
    default_moneris_device_name = fields.Char(
        string='Default Moneris Terminal ID',)

    cloud_terminal_id = fields.Char(
        "Moneris Device ID", related='moneris_device_id.code', help="The ECR number of the particular PINpad you are addressing", )

    moneris_cloud_set_tip = fields.Boolean("Moneris Cloud TIP set", default=False)
    moneris_cloud_tip_percentage = fields.Boolean("Display Percentage Selection", default=False)
    moneris_cloud_tip_amount = fields.Boolean("Display Amount Selection", default=False)

    is_moneris_go_cloud = fields.Boolean("Is Moneris Go Cloud?", default=False)

    # =========================================  Odoo 18 Payment Method Data load to POS ========================================
    @api.model
    def _load_pos_data_fields(self, config_id):
        params = super()._load_pos_data_fields(config_id)
        params += ['cloud_merchant_id','company_id',
                   'cloud_terminal_id', 'cloud_store_id','token','is_moneris_go_cloud']
        return params

    # ===========================================================================================================================



    def wizard_message(self, title, message):
        view = self.env.ref('payment_moneris_cloud.sh_message_wizard')
        view_id = view and view.id or False
        context = dict(self.env.context or {})
        context['message'] = message
        return {
            'name': title,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }

    def _compute_urls(self):
        if self.cloud_cloud_environment == 'test':
            self.cloud_inout_url = 'https://ippostest.moneris.com/Terminal/'
            self.cloud_out_url1 = 'https://iptermtest.moneris.com'
            self.cloud_out_url2 = 'https://cloudreceiptct.moneris.com'
        if self.cloud_cloud_environment == 'enabled':
            self.cloud_inout_url = 'https://ippos.moneris.com/Terminal/'
            self.cloud_out_url1 = 'https://ipterm.moneris.com'
            self.cloud_out_url2 = 'https://cloudreceipt.moneris.com'

    def cloud_terminal_pair(self):
        self._compute_urls()
        if self.cloud_store_id != False or self.cloud_api_token != False or self.cloud_terminal_id != False or self.cloud_pairing_token != False:
            json_request = {
                "storeId": self.cloud_store_id,
                "apiToken": self.cloud_api_token,
                "txnType": "pair",
                # "postbackUrl":"https://moneris.syray.com/moneriscloud/json",
                "terminalId": self.cloud_terminal_id,
                "request": {
                    "pairingToken": self.cloud_pairing_token
                }
            }
            pprint(json_request)
            if self.cloud_integration_method != 'polling':
                json_request['postbackUrl'] = self.cloud_postback_url
            try:
                _logger.info("Pairing Request-->")
                _logger.info(json_request)
                response = requests.post(
                    self.cloud_inout_url, json=json_request)
                _logger.info("Pairing Response-->")
                _logger.info(response)

                if response.status_code != 200:
                    raise exceptions.UserError(_("%s") % str(response))
                else:
                    if response:
                        resJson = response.json()
                        if resJson['receipt']['Error'] == "true":
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        # Required>>>>????
                        if resJson['receipt']['ResponseCode'] != '001':
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        else:
                            if resJson['receipt']['Error'] == "false":
                                receiptUrl = resJson['receipt']['receiptUrl']
                                responseTrue = False
                                while responseTrue != True:
                                    res = requests.get(receiptUrl)
                                    if res:
                                        res = res.json()
                                        if res['receipt']['Error'] == "false":
                                            if res['receipt']['Completed'] == "true":
                                                responseTrue = True
                                                _logger.info(
                                                    "Pairing Completed")
                                                print("Pairing Completed")
                                                self.cloud_cloud_paired = True
                                                # return self.wizard_message('Moneris Cloud Success', 'Pinpad Pairing Successful!')

                                        else:
                                            raise exceptions.UserError(
                                                _("Exception: %s") % res['receipt']['Message'])
            except Exception as e:
                _logger.warning("Pairing Exception %s", e)
                raise exceptions.UserError(_("Exception occured: %s") % e)

    def cloud_terminal_unpair(self):
        self._compute_urls()
        if self.cloud_store_id != False or self.cloud_api_token != False or self.cloud_terminal_id != False or self.cloud_pairing_token != False:
            json_request = {
                "storeId": self.cloud_store_id,
                "apiToken": self.cloud_api_token,
                "terminalId": self.cloud_terminal_id,
                "txnType": "unpair",
                # "postbackUrl":"https://example.client.url",
            }
            if self.cloud_integration_method != 'polling':
                json_request['postbackUrl'] = self.cloud_postback_url
            try:
                _logger.info("Unpair Request")
                _logger.info(json_request)
                response = requests.post(
                    self.cloud_inout_url, json=json_request)
                print(response.text)
                if response.status_code != 200:
                    raise exceptions.UserError(_("%s") % str(response))
                else:
                    if response:
                        resJson = response.json()
                        if resJson['receipt']['Error'] == "true":
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        # Required>>>????
                        if resJson['receipt']['ResponseCode'] != '001':
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        else:
                            if resJson['receipt']['Error'] == "false":
                                receiptUrl = resJson['receipt']['receiptUrl']
                                responseTrue = False
                                while responseTrue != True:
                                    res = requests.get(receiptUrl)
                                    print(res)
                                    if res:
                                        res = res.json()
                                        if res['receipt']['Error'] == "false":
                                            if res['receipt']['Completed'] == "true":
                                                responseTrue = True
                                                _logger.info(
                                                    "Un Pairing Completed")
                                                print("Un Pairing Completed")
                                                self.cloud_cloud_paired = False
                                        else:
                                            raise exceptions.UserError(
                                                _("Exception: %s") % res['receipt']['Message'])
            except Exception as e:
                _logger.warning("Pairing Exception %s", e)
                raise exceptions.UserError(_("Exception occured: %s") % e)

    def cloud_terminal_init(self):
        print("cloud_terminal_init")
        self._compute_urls()
        if self.cloud_store_id != False or self.cloud_api_token != False or self.cloud_terminal_id != False or self.cloud_pairing_token != False:
            json_request = {
                "storeId": self.cloud_store_id,
                "apiToken": self.cloud_api_token,
                "terminalId": self.cloud_terminal_id,
                "txnType": "initialization",
                # "postbackUrl":"https://example.client.url",
            }
            try:
                print(json_request)
                if self.cloud_integration_method != 'polling':
                    json_request['postbackUrl'] = self.cloud_postback_url
                response = requests.post(
                    self.cloud_inout_url, json=json_request)
                print(response.text)
                if response:
                    resJson = response.json()
                    if resJson['receipt']['Error'] == "true":
                        raise exceptions.UserError(
                            _("Exception: %s") % resJson['receipt']['Message'])
                    # Required>>>????
                    if resJson['receipt']['ResponseCode'] != '001':
                        raise exceptions.UserError(
                            _("Exception: %s") % resJson['receipt']['Message'])
                    if resJson['receipt']['Error'] == "false":
                        receiptUrl = resJson['receipt']['receiptUrl']
                        responseTrue = False
                        while responseTrue != True:
                            res = requests.get(receiptUrl)
                            if res:
                                res = res.json()
                                if res['receipt']['Error'] == "false":
                                    if res['receipt']['Completed'] == "true":
                                        responseTrue = True
                                        print("Initialization Completed")
                                        _logger.info(
                                            "Initialization Completed")
                                        # return self.wizard_message('Moneris Cloud Success', 'Pinpad Initilization Successful!')
                                        # '{"receipt":{"Completed":"true","TransType":"90","Error":"false",
                                        # "InitRequired":"false","TransDateTime":"200918082131",
                                        # "TerminalId":"P1503106","Timer":null,"ResponseCode":"007",
                                        # "TCRRL":"0000","CloudTicket":"98a6f1fb-047a-4e4b-8dc7-c125b544efbc",
                                        # "TxnName":"Initialization"}}'

                    else:
                        raise exceptions.UserError(
                            _(resJson['receipt']['Message']))
                print("cloud_terminal_init-->res-->")
                print(response.text)
                if response.status_code != 200:
                    raise exceptions.UserError(_("%s") % str(response))
                else:
                    self.cloud_cloud_paired = False
            except Exception as e:
                _logger.info("Exception occured %s", e)
                raise exceptions.UserError(_("Exception occured: %s") % e)


    # ============== Set TIP =================
    @api.onchange('moneris_cloud_tip_percentage', 'moneris_cloud_tip_amount')
    def _onchange_tip_features(self):
        for rec in self:
            if rec.moneris_cloud_set_tip == True:
                raise UserError(_("You can not change feature while tip is set already!"))


    def cloud_terminal_set_tip(self):
        self._compute_urls()
        if self.cloud_store_id != False or self.cloud_api_token != False or self.cloud_terminal_id != False or self.cloud_pairing_token != False:
            set_tip = self.env.context.get('set_tip')
            fields.Many2one('ir.config_parameter')
            # odoo_tip = self.env['res.config.settings'].pos_iface_tipproduct
            # if not odoo_tip:
            #     raise UserError(_("Please enable Tip feature from settings."))
            json_request = {
                "storeId": self.cloud_store_id,
                "apiToken": self.cloud_api_token,
                "txnType": "setTip",
                "terminalId": self.cloud_terminal_id,

            }
            if set_tip:
                json_request["request"] = {
                    "enableTip": "1",
                    "displayPercentageSelection": "1" if self.moneris_cloud_tip_percentage else "0",
                    "displayAmountSelection": "1" if self.moneris_cloud_tip_amount else "0",
                }
            else:
                json_request["request"] = {
                    "enableTip": "0",
                }
            pprint(json_request)
            if self.cloud_integration_method != 'polling':
                json_request['postbackUrl'] = self.cloud_postback_url
            try:
                _logger.info("Pairing Request-->")
                _logger.info(json_request)
                response = requests.post(
                    self.cloud_inout_url, json=json_request)
                _logger.info("Set Tip Response-->")
                _logger.info(response)

                if response.status_code != 200:
                    raise exceptions.UserError(_("%s") % str(response))
                else:
                    if response:
                        resJson = response.json()
                        if resJson['receipt']['Error'] == "true":
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        # Required>>>>????
                        if resJson['receipt']['ResponseCode'] != '001':
                            raise exceptions.UserError(
                                _("Exception: %s") % resJson['receipt']['Message'])
                        else:
                            if resJson['receipt']['Error'] == "false":
                                receiptUrl = resJson['receipt']['receiptUrl']
                                responseTrue = False
                                while responseTrue != True:
                                    res = requests.get(receiptUrl)
                                    if res:
                                        res = res.json()
                                        if res['receipt']['Error'] == "false":
                                            if res['receipt']['Completed'] == "true":
                                                responseTrue = True
                                                _logger.info(
                                                    "Tip set Completed")
                                                print("Tip Set Completed")
                                                self.moneris_cloud_set_tip = True if set_tip else False
                                                # return self.wizard_message('Moneris Cloud Success', 'Pinpad Pairing Successful!')

                                        else:
                                            raise exceptions.UserError(
                                                _("Error Code: %s") % res['receipt'].get('ErrorCode'))
            except Exception as e:
                _logger.warning("Pairing Exception %s", e)
                raise exceptions.UserError(_("Exception occured: %s") % e)

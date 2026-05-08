import requests
from odoo import api, fields, models,_

import  logging
_logger = logging.getLogger(__name__)

class OmniAccountPosPayment(models.Model):
    _inherit = "omni.account"

    pos_payment_methods_ids = fields.One2many(
        string="POS Payment Methods",
        comodel_name="pos.payment.method",
        inverse_name="account_id"
    )

    def process_pos_payment_subscriptions(self, kwargs, subscription):

        kwargs=super(OmniAccountPosPayment, self).process_pos_payment_subscriptions(kwargs, subscription)

        pos_payment_method = self.env['pos.payment.method']
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = pos_payment_method.search(domain, limit=1)

        if not existing_service:
            journal = self.env['account.journal'].search(
                [("token", "=", subscription.get("service_key")), ('company_id', '=', self.company_id.id)], limit=1)
            kwargs["messages"] += "\n" + subscription.get("service_name").upper()
            created_val = {
                "name": subscription.get("service_name").upper(),
                "company_id": self.company_id.id,
                "omnisync_active": True,
                "account_id": self.id,

                "use_payment_terminal": subscription.get("service_name"),
                "payment_method_type":'terminal',

                "token": subscription.get("service_key"),
            }
            if subscription.get("service_name") == 'clover_cloud':
                created_val.update({
                    'journal_id': journal.id,
                    'payment_method_type': "terminal",
                    'clover_server_url': journal.clover_server_url,
                    'clover_config_id': journal.clover_config_id,
                    'clover_jwt_token': journal.clover_jwt_token,
                    'clover_merchant_id': journal.clover_merchant_id
                })
            if subscription.get("service_name") == 'moneris_cloud':
                    moneris_device = self.env['moneris.device']
                    exist_moneris_device= moneris_device.search([('code','=',journal.cloud_terminal_id)],limit=1)

                    if exist_moneris_device:
                        device_id = exist_moneris_device
                    else:
                        terminal_id = journal.cloud_terminal_id if journal.cloud_terminal_id != "" else "Test"
                        device_id = moneris_device.create({
                            "name": terminal_id,
                            "code": terminal_id,
                        })

                    created_val.update({
                        'journal_id': journal.id,
                        'cloud_store_id': journal.cloud_store_id,
                        'cloud_api_token': journal.cloud_api_token,
                        'moneris_device_id': device_id.id,
                        'cloud_pairing_token': "77777"
                    })

            if subscription.get("service_name") == 'moneris_cloud_go':
                    moneris_device = self.env['moneris.device']
                    exist_moneris_device= moneris_device.search([('code','=',journal.cloud_terminal_id)],limit=1)

                    if exist_moneris_device:
                        device_id = exist_moneris_device
                    else:
                        terminal_id = journal.cloud_terminal_id if journal.cloud_terminal_id != "" else "Test"
                        device_id = moneris_device.create({
                            "name": terminal_id,
                            "code": terminal_id,
                        })

                    created_val.update({
                        'journal_id': journal.id,
                        'cloud_store_id': journal.cloud_store_id,
                        'cloud_api_token': journal.cloud_api_token,
                        'moneris_device_id': device_id.id,
                        'cloud_pairing_token': "77777",
                        "is_moneris_go_cloud":True,
                        "use_payment_terminal":'moneris_cloud'
                    })

            try:
                created_payment = pos_payment_method.create(created_val)
                _logger.info(created_payment)
            except Exception as e:
                _logger.warning(_(e))
        else:
            kwargs["error_messages"] += (
                    subscription.get("service_name").upper() + " already exists!"
            )
        return kwargs
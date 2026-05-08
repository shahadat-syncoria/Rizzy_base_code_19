# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo.addons.odoosync_base.utils.helper import image_processing
from odoo import api, fields, models

import requests
import logging

_logger = logging.getLogger(__name__)


class OmniAccountPayment(models.Model):
    _inherit = "omni.account"

    provider_ids = fields.One2many(
        string="Payment providers",
        comodel_name="payment.provider",
        inverse_name="account_id",
    )
    journal_ids = fields.One2many(
        string="Account Journals",
        comodel_name="account.journal",
        inverse_name="account_id"
    )

    def process_subscriptions(self, res_json):
        kwargs = super(OmniAccountPayment, self).process_subscriptions(res_json)
        for subscription in kwargs["all_subscriptions"].get("payment"):
            if not subscription.get("service_name").endswith("cloud") and  subscription.get("service_name") not in ['moneris_cloud_go']:
                kwargs = self.process_payment_subscriptions(kwargs, subscription)
                continue
            else:
                kwargs = self.process_pos_payment_subscriptions(kwargs,subscription)
        return kwargs

    def process_payment_subscriptions(self, kwargs, subscription):
        """[summary]

        Args:
            kwargs ([type]): [description]
            subscription ([type]): [description]
        """

        payment_provider = self.env["payment.provider"].sudo()
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = payment_provider.search(domain, limit=1)
        if not existing_service:
            kwargs["messages"] += "\n" + subscription.get("service_name").upper()

            created_val = {
                "name": subscription.get("service_name").upper(),
                "code": subscription.get("service_name"),
                "company_id": self.company_id.id,
                "omnisync_active": True,
                "account_id": self.id,
                "token": subscription.get("service_key"),
                "module_id": self.env['ir.module.module'].sudo().search([("name", "=", 'os_payment')], limit=1).id
            }
            if subscription.get("service_name") == 'clik2pay':
                created_val.update({
                    "code": "clik2pay",
                    "name": "Clik2pay Payment",
                    # "display_as": "Clik2pay via Interac",
                    "redirect_form_view_id": self.env.ref(
                        "os_payment.clik2pay_redirect_form"
                    ).id,
                    # "payment_flow":"s2s"
                    "available_country_ids": [(6, 0, [self.env.ref("base.ca")])],
                    "payment_method_ids": [(6, 0, [
                        self.env.ref(
                            "os_payment.payment_icon_via_interac_icon"
                        ).id
                    ])],

                    # "image_128": image_processing(image_path="os_payment/static/src/img/clik2pay_payment/icon.png")
                })
            if subscription.get("service_name") == 'moneris':
                created_val.update({
                    "code": "monerischeckout",
                    "name": "Moneris Checkout",
                    "inline_form_view_id": self.env.ref("os_payment.moneris_inline_form").id,
                    #"image_128": image_processing(image_path="os_payment/static/src/img/moneris_checkout"
                                    #                         "/moneris_checkout.png"),
                    "payment_method_ids": [(6, 0, [
                        self.env.ref(
                            "os_payment.payment_method_moneris_checkout"
                        ).id
                    ])],
                })
            elif subscription.get("service_name") == 'bambora_checkout':
                created_val.update({
                    "code": "bamborachk",
                    "name": "Bambora Checkout",
                    # "display_as": "Bambora Checkout",
                    "inline_form_view_id": self.env.ref(
                        "os_payment.bamborachk_inline_form"
                    ).id,
                    "payment_method_ids": [(6, 0, [
                        self.env.ref("os_payment.payment_method_bambora").id
                        ])],
                    # "payment_flow":"s2s"
                    "image_128": image_processing(image_path="os_payment/static/src/img/bambora_checkout/icon.png")
                })
            elif subscription.get("service_name") == 'clover_checkout':
                try:
                    details = self.fetch_service_details(endpoint=subscription.get("detail"))
                    created_val.update({
                        "code": "clover_checkout",
                        "name": "Clover Checkout",
                        "display_name": "Clover Checkout",
                        "clover_public_api_key": details.get('clover_public_api_key'),
                        "allow_tokenization": True,
                        "allow_express_checkout": True,
                        "payment_method_ids": [(6, 0, [
                            self.env.ref("os_payment.payment_method_clover").id
                        ])],
                        # "inline_form_view_id": self.env.ref(
                        #     "os_payment.inline_form_clover_checkout"
                        # ).id,
                        # "redirect_form_view_id": self.env.ref(
                        #     "os_payment.clik2pay_redirect_form"
                        # ).id,
                        # "payment_flow":"s2s"
                        # "available_country_ids": [(6, 0, [self.env.ref("base.ca")])],
                        #         "payment_icon_ids": [(6, 0, [
                        #             self.env.ref(
                        #                 "os_payment.payment_icon_via_interac_icon"
                        #             ).id
                        # ])],
                        # "redirect_form_view_id": self.env.ref(
                        #     "os_payment.clover_redirect_form"
                        # ).id,
                        # "image_128": image_processing(image_path="os_payment/payment_apps/payment_globalpay/static/src/img/icon.png")
                        # "image_128": image_processing(image_path="/static/src/img/payment_clover_checkout/logo.svg")
                    })
                except Exception as e:
                    _logger.info("Payment Method Creation Failed")
                    kwargs["error_messages"] += (
                            subscription.get("service_name").upper() + f": Payment Method Creation Failed\nReason: {e}"
                    )
                    return kwargs

            elif subscription.get("service_name") == 'resolve':
                self.env['resolvepay.instance'].create({
                    "name": subscription.get("service_name"),
                    "token": subscription.get("service_key"),
                    "company_id": self.company_id.id
                })
            # elif subscription.get("service_name") == 'clik2pay':
            #     created_val.update({
            #         "code": "clik2pay",
            #         "name": "Clik2pay Payment",
            #         "display_as": "Clik2pay via Interac",
            #         "redirect_form_view_id": self.env.ref(
            #             "os_payment.clik2pay_redirect_form"
            #         ).id,
            #         # "payment_flow":"s2s"
            #         "available_country_ids":[(6, 0, [self.env.ref("base.ca")])],
            #         "payment_icon_ids": [(6, 0, [
            #             self.env.ref(
            #                 "os_payment.payment_icon_via_interac_icon"
            #             ).id
            # ])],
            #
            #         # "image_128": image_processing(image_path="os_payment/static/src/img/clik2pay_payment/icon.png")
            #     })
            elif subscription.get("service_name") == 'rotessa':
                created_val.update({
                    "code": "rotessa",
                    "name": "Rotessa Payment",
                    # "display_as": "Rotessa Paymemnt",
                    # "redirect_form_view_id": self.env.ref(
                    #     "os_payment.clik2pay_redirect_form"
                    # ).id,
                    # "payment_flow":"s2s"
                    "available_country_ids":[(6, 0, [self.env.ref("base.ca")])],
            #         "payment_icon_ids": [(6, 0, [
            #             self.env.ref(
            #                 "os_payment.payment_icon_via_interac_icon"
            #             ).id
            # ])],
                })
            elif subscription.get("service_name") == 'global_payment':
                created_val.update({
                    "code": "globalpay",
                    "name": "GlobalPay",
                    # "display_as": "GlobalPay",
                    "allow_tokenization": True,
                    "allow_express_checkout": True,
                    # "redirect_form_view_id": self.env.ref(
                    #     "os_payment.clik2pay_redirect_form"
                    # ).id,
                    # "payment_flow":"s2s"
                    "available_country_ids": [(6, 0, [self.env.ref("base.ca")])],
                    "payment_method_ids": [(6, 0, [
                        self.env.ref(
                            "os_payment.payment_method_for_global"
                        ).id
                    ])],
                    "redirect_form_view_id": self.env.ref(
                        "os_payment.globalpay_redirect_form"
                    ).id,
                    # "image_128": image_processing(image_path="os_payment/payment_apps/payment_globalpay/static/src/img/icon.png")
                    "image_128": image_processing(image_path="os_payment/static/src/img/global_payment/icon.png")
                })
            try:
                created_payment = payment_provider.create(created_val)
                created_payment._cr.commit()
                _logger.info("Payment Method Creation Complete: ===>>>{}".format(created_payment))
            except Exception as e:
                _logger.info("Payment Method Creation Failed")
                kwargs["error_messages"] += (
                        subscription.get("service_name").upper() + f": Payment Method Creation Failed\nReason: {e}"
                )
        else:
            kwargs["error_messages"] += (
                    subscription.get("service_name").upper() + " already exists!"
            )

        # if subscription.get("service_name").endswith("cloud"):
        #     kwargs = self.process_pos_payment_subscriptions(kwargs, subscription)

        return kwargs

    def process_pos_payment_subscriptions(self, kwargs, subscription):
        journal = self.env['account.journal']
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = journal.search(domain, limit=1)

        if not existing_service:
            journal = self.env['account.journal'].search(
                [("type", "=", "bank"), ('company_id', '=', self.company_id.id)], limit=1)
            kwargs["messages"] += "\n" + subscription.get("service_name").upper()
            if subscription.get("service_name") == 'clover_cloud':
                server_url = self.server_url + subscription.get('detail')
                headers = {"Authorization": "Token %s" % (self.token)}
                response = requests.request("GET", server_url, headers=headers)
                if response.status_code == 200:
                    res_json = response.json()
                    new_clover_journal = journal.copy()
                    new_clover_journal.write({
                        "name": subscription.get("service_name").upper(),
                        "omnisync_active": True,
                        "account_id": self.id,
                        "token": subscription.get("service_key"),
                        "use_clover_terminal": True,
                        'clover_server_url': res_json.get('clover_server_url'),
                        'clover_config_id': res_json.get('clover_config_id'),
                        'clover_jwt_token': res_json.get('clover_token'),
                        'clover_merchant_id': res_json.get('clover_merchant_id')

                    })
            if subscription.get("service_name") == 'moneris_cloud':
                existing_moneris= journal.search([("use_cloud_terminal","=",True)])
                server_url = self.server_url + subscription.get('detail')
                headers = {"Authorization": "Token %s" % (self.token)}
                response = requests.request("GET", server_url, headers=headers)
                if response.status_code == 200:
                    res_json = response.json()
                    new_moneris_journal = journal.copy()
                    new_moneris_journal.write({
                        "name": subscription.get("service_name").upper()+"-"+str(len(existing_moneris)+1),
                        "use_cloud_terminal": True,
                        "omnisync_active": True,
                        "account_id": self.id,

                        "token": subscription.get("service_key"),
                        'cloud_store_id': res_json.get('store_id'),
                        'cloud_api_token': res_json.get('api_token'),
                        'cloud_terminal_id': res_json.get('terminal_id'),
                        'cloud_pairing_token': "77777"

                    })

            if subscription.get("service_name") == 'moneris_cloud_go':
                existing_moneris= journal.search([("use_cloud_terminal","=",True),("is_moneris_go_cloud","=",True)])
                server_url = self.server_url + subscription.get('detail')
                headers = {"Authorization": "Token %s" % (self.token)}
                response = requests.request("GET", server_url, headers=headers)
                if response.status_code == 200:
                    res_json = response.json()
                    new_moneris_journal = journal.copy()
                    new_moneris_journal.write({
                        "name": subscription.get("service_name").upper()+"-"+str(len(existing_moneris)+1),
                        "use_cloud_terminal": True,
                        "omnisync_active": True,
                        "account_id": self.id,
                        "is_moneris_go_cloud":True,

                        "token": subscription.get("service_key"),
                        'cloud_store_id': res_json.get('store_id'),
                        'cloud_api_token': res_json.get('api_token'),
                        'cloud_terminal_id': res_json.get('terminal_id'),
                        'cloud_pairing_token': "77777"

                    })
        else:
            kwargs["error_messages"] += (
                    subscription.get("service_name").upper() + " already exists!"
            )
        return kwargs

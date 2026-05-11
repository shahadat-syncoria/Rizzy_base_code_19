# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import requests
import logging
from ..utils.delivery_data import DataUtils

_logger = logging.getLogger(__name__)


MODULES = {
    "is_delivery": "os_delivery",
    "is_delivery_website":"os_delivery_website",
    "is_payment":"os_payment",
    "is_payment_website":"os_payment_website",
    "is_payment_pos":"os_payment_pos"
}


class OmniAccount(models.Model):
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _name = "omni.account"
    _description = "Omni Account"
    _order = "id desc"

    name = fields.Char(
        string="Instance Name",
        required=True,
        copy=False,
        index=True,
        default=lambda self: _("New"),
    )
    # Options
    company_id = fields.Many2one("res.company", ondelete="restrict", required=True)
    state = fields.Selection(
        [("draft", "Not Confirmed"), ("active", "Active"), ("inactive", "Inactive")],
        default="draft",
        string="State",
    )
    client_id = fields.Char('Client Id', copy=False)
    server_url = fields.Char(required=True, copy=False)
    os_user_id = fields.Char("Username", required=True, copy=False)
    user_id = fields.Many2one('res.users', ondelete='restrict')
    token = fields.Char(required=True, copy=False)
    debug_logging = fields.Boolean()
    active = fields.Boolean(default=True)

    # Odoo Sync Modules
    is_delivery = fields.Boolean(string="Delivery", tracking=True)
    is_delivery_website = fields.Boolean(string="Website Delivery", tracking=True)

    is_payment = fields.Boolean(string="Payment", tracking=True)
    is_payment_website = fields.Boolean(string="Website Payment", tracking=True)
    is_payment_pos = fields.Boolean(string="POS Payment", tracking=True)

    syncoria_pos_token = fields.Char('Syncoria POS Token', copy=False)



    def _module_check_install(self):
        module_list = []
        if self.is_delivery:
            module_list += [MODULES.get('is_delivery')]
        if self.is_delivery_website:
            module_list += [MODULES.get('is_delivery_website')]
        if self.is_payment:
            module_list += [MODULES.get('is_payment')]
        if self.is_payment_website:
            module_list += [MODULES.get('is_payment_website')]
        if self.is_payment_pos:
            module_list += [MODULES.get('is_payment_pos')]

        ir_module = self.env['ir.module.module'].sudo()

        for module in module_list:
            module_id = ir_module.search([('name', '=', module)], limit=1)

            if module_id.state == 'installed':
                pass
                # module_id.button_immediate_upgrade()
            else:
                module_id.button_immediate_install()


    def write(self, values):
        if values.get("state") == "active":
            # domain = [("state", "=", "active"), ('company_id', '=', self.company_id.id)]
            # records = self.env["omni.account"].sudo().search(domain)
            # if records:
            #     raise UserError(
            #         _(
            #             "You already have a Omni Account Activated. You can not activate another account."
            #         )
            #     )

            record = self.env["omni.account"].sudo().search([("token", "=", values.get("token"))])
            if record:
                raise UserError(
                    _(
                        "You already have a Omni Account Registered with this user."
                    )
                )
        result = super(OmniAccount, self).write(values)
        if result:
            self._module_check_install()
        return result

    @api.model_create_multi
    def create(self, vals):
        for rec in self:
            if vals.get("token"):
                domain = [("token", "=", vals.get("token"))]
                records = self.env["omni.account"].sudo().search(domain)
                if records:
                    raise UserError(
                        _(
                            "You already have a Omni Account Registered with this user."
                        )
                    )
        result = super(OmniAccount, self).create(vals)
        for rec in result:
            if rec:
                rec._module_check_install()
        return result
    

    def toggle_debug(self):
        for c in self:
            c.debug_logging = not c.debug_logging

    def action_activate(self):
        """[Button Action to Activate Odoo Sync Instance]

        Raises:
            UserError: [Activation Error]
        """

        try:
            result = self.fetch_services()
            if result:
                result = {
                    "name": "Fetch Service",
                    "model": "omni.account",
                    "messages": result.get("messages"),
                    "error_messages": result.get("error_messages"),
                }
                self.create_logging(result)
                self.write({"state": "active"})

        except Exception as e:
            raise UserError(_("Error: %s", e.args))

    def action_deactivate(self):
        """[Button Action to Deactivate Odoo Sync Instance]

        Raises:
            UserError: [Activation Error]
        """
        if self.state == "active":
            self.state = "inactive"

    def test_omni_connection(self):
        """[Button Action to Test Odoo Sync Server Connection]

        Raises:
            UserError: [Server Connection Error]
        """
        try:
            server_url = self.server_url + "/auth/users/"
            headers = {"Authorization": "Token %s" % (self.token)}

            response = requests.request(method="GET", url=server_url, headers=headers)
            messages = (
                "Everything seems properly set up!"
                if response.status_code == 200
                else "Server Credentials are wrong. Please Check credentials!"
            )
            error_messages = (
                "Server Credentials are wrong. Please Check"
                if response.status_code != 200
                else ""
            )
            if response.status_code != 200:
                error_messages = "Server Credentials are wrong. Please Check"
                raise UserError(_(messages))

            title = _("Connection Test Succeeded!")

            if self.debug_logging:
                _logger.info("Server Url ===>>> %s" % server_url)
                _logger.info("headers ===>>>%s" % headers)
                _logger.info("response ===>>>%s" % response)
                data = {
                    "name": "Test Connection",
                    "company_id": self.company_id,
                    "model": self._name,
                    "messages": messages,
                    "error_messages": error_messages,
                }
                self.create_logging(data)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": title,
                    "message": messages,
                    "sticky": False,
                },
            }
        except Exception as e:
            raise UserError(_("Error: %s", e.args))

    def fetch_services(self):
        """API Request to Fetch the Services

        Returns:
            [requests.response]]: [Fetch Services Response]
        """
        try:
            result = False
            server_url = self.server_url + "/api/v1/services/subscriptions/"
            headers = {"Authorization": "Token %s" % (self.token)}
            response = requests.request("GET", server_url, headers=headers)
            if response.status_code == 200:
                res_json = response.json()
                result = self.process_subscriptions(res_json)
            else:
                raise UserError(_("Error: %s", response.text))

            return result

        except Exception as e:
            raise UserError(_("Error: %s", e.args))

    def fetch_service_details(self, endpoint):
        """API Request to Fetch the Services

        Returns:
            [requests.response]]: [Fetch Services Response]
        """
        try:
            server_url = self.server_url + endpoint
            headers = {"Authorization": "Token %s" % (self.token)}
            response = requests.request("GET", server_url, headers=headers)
            if response.status_code == 200:
                res_json = response.json()
            else:
                raise UserError(_("Error: %s", response.text))

            return res_json


        except Exception as e:
            raise UserError(_("Error: %s", e.args))


    def _delivery_data_creation(self):
        try:
            product_tmpl = self.env["product.template"]
            for data in DataUtils.delivery_product_data():
                product_exist = product_tmpl.search(
                    [("default_code", "=", data.get("default_code")), ("company_id", "=", self.company_id.id)])
                if not product_exist:
                    data['company_id'] = self.company_id.id
                    product_tmpl.create(data)
                    product_tmpl._cr.commit()
        except Exception as e:
            raise (e)

    def process_subscriptions(self, res_json):
        """[Function to Process Subscriptions]

        Args:
            res_json ([dict]): [Response Dict]
        """
        kwargs = {}
        kwargs["messages"] = ""
        kwargs["error_messages"] = ""
        total_subscriptions = res_json["count"]
        _logger.info("total_subscriptions ===>>> %s", total_subscriptions)

        # Note : Please maintain This code convention
        # subs_(service_type)

        subs_delivery = []
        subs_paymentgateway = []
        subs_marketplace = []
        subs_pointofsale = []
        for subscription in res_json["results"]:
            exec(f"subs_{subscription.get('service_type').lower()}.append({subscription})")
        kwargs["all_subscriptions"] = {
            "delivery": subs_delivery,
            "payment": subs_paymentgateway,
            "marketplace": subs_marketplace,
            "point_of_sale": subs_pointofsale
        }
        for subscription in kwargs["all_subscriptions"].get("point_of_sale"):
            self.syncoria_pos_token = subscription.get('service_key')
        return kwargs

    def process_mktplace_subscriptions(self, kwargs, subscription):
        """[Process Marketplace Subscriptions]
        Args:
            res_json ([dict]): [Response Dict]
        """
        mktplc_instance = self.env['marketplace.instance'].sudo()
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = mktplc_instance.search(domain, limit=1)

        if not existing_service:
            language_id = self.env['res.lang'].sudo().search([('code', '=', self.env.user.lang)], limit=1).id
            warehouse_id = self.env['stock.warehouse'].search([('company_id', 'in', self.company_id.ids)], limit=1).id
            created_service = mktplc_instance.create({
                "name": subscription.get("service_name").upper(),
                "marketplace_instance_type": subscription.get("service_name"),
                "token": subscription.get("service_key"),
                # Credentials
                "marketplace_secret_key": subscription.get("secret_key"),
                "marketplace_host": subscription.get("shop_url"),
                "marketplace_country_id": self.env.user.company_id.id,
                "marketplace_api_key": subscription.get("api_key"),
                "marketplace_api_password": subscription.get("password"),
                "marketplace_api_version": subscription.get("api_version"),
                # Options
                "company_id": self.company_id.id,
                "warehouse_id": warehouse_id,
                "user_id": self.env.user.id,
                "language_id": language_id,
            })
            _logger.info(created_service)

            kwargs["messages"] += "\n Marketplace Created:" + str(subscription.get("service_name").upper())
        else:
            kwargs["error_messages"] += "" + str(subscription.get("service_name").upper()) + ' already exists!'

        return kwargs

    def process_pos_payment_subscriptions(self, kwargs, subscription):
        """[Process POS Payment Subscriptions]
        Args:
            res_json ([dict]): [Response Dict]
        """
        pos_payment_method = self.env['pos.payment.method']
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = pos_payment_method.search(domain, limit=1)

        if not existing_service:
            journal = self.env['account.journal'].search(
                [("type", "=", "bank"), ('company_id', '=', self.company_id.id)], limit=1)
            kwargs["messages"] += "\n" + subscription.get("service_name").upper()
            created_val = {
                "name": subscription.get("service_name").upper(),
                "company_id": self.company_id.id,
                "omnisync_active": True,
                "account_id": self.id,
                "use_payment_terminal": subscription.get("service_name"),
                "token": subscription.get("service_key"),
            }
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
                    created_val.update({
                        'journal_id': new_clover_journal.id,
                        'clover_server_url': res_json.get('clover_server_url'),
                        'clover_config_id': res_json.get('clover_config_id'),
                        'clover_jwt_token': res_json.get('clover_token'),
                        'clover_merchant_id': res_json.get('clover_merchant_id')
                    })
            if subscription.get("service_name") == 'moneris_cloud':
                existing_moneris = journal.search([("use_cloud_terminal", "=", True)])
                server_url = self.server_url + subscription.get('detail')
                headers = {"Authorization": "Token %s" % (self.token)}
                response = requests.request("GET", server_url, headers=headers)
                if response.status_code == 200:
                    res_json = response.json()
                    new_moneris_journal = journal.copy()
                    new_moneris_journal.write({
                        "name": subscription.get("service_name").upper() + "-" + str(len(existing_moneris) + 1),
                        "use_cloud_terminal": True,
                        "omnisync_active": True,
                        "account_id": self.id,

                        # "purolator_developer_key": "test",
                        "token": subscription.get("service_key"),
                        'cloud_store_id': res_json.get('store_id'),
                        'cloud_api_token': res_json.get('api_token'),
                        'cloud_terminal_id': res_json.get('terminal_id'),
                        'cloud_pairing_token': "77777"

                    })
                    created_val.update({
                        'journal_id': new_moneris_journal.id,
                        'cloud_store_id': res_json.get('store_id'),
                        'cloud_api_token': res_json.get('api_token'),
                        'cloud_terminal_id': res_json.get('terminal_id'),
                        'cloud_pairing_token': "77777"
                    })

            try:
                created_payment = pos_payment_method.create(created_val)
                _logger.info(created_payment)
            except Exception as e:
                _logger(_(e))
        else:
            kwargs["error_messages"] += (
                    subscription.get("service_name").upper() + " already exists!"
            )
        return kwargs

    def create_logging(self, data):
        """Function to create a logging

        Args:
            data (dict): A dict containing: name, model, messages,error_messages
        """
        omni_log = self.env["omni.logging"].sudo()
        return omni_log.create(
            {
                "name": data.get("name", ""),
                "company_id": self.company_id.id,
                "model": self._name,
                "messages": data.get("messages", ""),
                "error_messages": data.get("error_messages", ""),
                "level": "test",
            }
        )



# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models
import logging


_logger = logging.getLogger(__name__)


class OmniAccountMarketplace(models.Model):
    _inherit = "omni.account"

    marketplace_ids = fields.One2many(
        string="Marketplace",
        comodel_name="marketplace.instance",
        inverse_name="account_id",
    )

    def process_subscriptions(self, res_json):
        kwargs = super(OmniAccountMarketplace, self).process_subscriptions(res_json)

        for subscription in kwargs["all_subscriptions"].get("marketplace"):
            kwargs = self.process_mktplace_subscriptions(kwargs, subscription)

        return kwargs

    def process_mktplace_subscriptions(self, kwargs, subscription):
        """[Process Marketplace Subscriptions]
        Args:
            res_json ([dict]): [Response Dict]
        """
        ir_module = self.env['ir.module.module'].sudo()
        module_id = ir_module.search([('name', '=', 'syncoria_'+subscription.get("service_name"))], limit=1)
        if module_id.state == 'installed':
            pass
        else:
            module_id.button_immediate_install()

        mktplc_instance = self.env['marketplace.instance'].sudo()
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = mktplc_instance.search(domain, limit=1)

        if not existing_service:
            language_id = self.env['res.lang'].sudo().search([('code', '=', self.env.user.lang)], limit=1).id
            created_service = mktplc_instance.create({
                "name": subscription.get("service_name").upper(),
                "marketplace_instance_type": subscription.get("service_name"),
                "token": subscription.get("service_key"),
                "account_id": self.id,
                # Options
                "company_id": self.company_id.id,
                "user_id": self.env.user.id,
                "language_id": language_id,
            })
            _logger.info(created_service)

            kwargs["messages"] += "\n Marketplace Created:" + str(subscription.get("service_name").upper())
        else:
            kwargs["error_messages"] += "" + str(subscription.get("service_name").upper()) + ' already exists!'

        return kwargs

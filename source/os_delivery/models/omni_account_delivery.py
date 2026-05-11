# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, fields, models
import logging


_logger = logging.getLogger(__name__)


class OmniAccountDelivery(models.Model):
    _inherit = "omni.account"

    carrier_ids = fields.One2many(
        string="Delivery Carriers",
        comodel_name="delivery.carrier",
        inverse_name="account_id",
    )

    def process_subscriptions(self, res_json):
        kwargs = super(OmniAccountDelivery, self).process_subscriptions(res_json)

        # Delivery Data Create
        self._delivery_data_creation()
        for subscription in kwargs["all_subscriptions"].get("delivery"):
            kwargs = self.process_delivery_subscriptions(kwargs, subscription)

        return kwargs

    def process_delivery_subscriptions(self, kwargs, subscription):
        """[summary]
        Args:
            res_json ([type]): [description]
        """
        delivery_carrier = self.env["delivery.carrier"].sudo()
        # Check exsiting service
        # domain = [("delivery_type", "=", subscription.get("service_name"))]
        domain = [("token", "=", subscription.get("service_key"))]
        existing_service = delivery_carrier.search(domain, limit=1)
        if not existing_service:
            kwargs["messages"] += "\n" + subscription.get("service_name").upper()

            created_val = {
                "name": subscription.get("service_name").upper(),
                "delivery_type": subscription.get("service_name"),
                "company_id": self.company_id.id,
                "integration_level": "rate_and_ship",
                "omnisync_active": True,
                "account_id": self.id,
                "token": subscription.get("service_key"),
            }
            if subscription.get("service_name") == 'purolator':
                created_val['product_id'] = self.env["product.product"].search(
                    [("default_code", "=", "Purolator_001"), ("company_id", "=", self.company_id.id)]).id
            elif subscription.get("service_name") == 'canadapost':
                created_val['product_id'] = self.env["product.product"].search(
                    [("default_code", "=", "DeliveryCNPOST"), ("company_id", "=", self.company_id.id)]).id
            try:
                created_delivery = delivery_carrier.create(created_val)
                _logger.info(created_delivery)
            except Exception as e:
                _logger.info("Payment Method Creation Failed")
                kwargs["error_messages"] += (
                        subscription.get("service_name").upper() + f":Delivery Creation Failed\nReason: {e}"
                )

        else:
            kwargs["error_messages"] += (
                    subscription.get("service_name").upper() + " already exists!"
            )

        return kwargs

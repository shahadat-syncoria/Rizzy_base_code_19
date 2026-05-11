# # -*- coding: utf-8 -*-
# ###############################################################################
# #    License, author and contributors information in:                         #
# #    __manifest__.py file at the root folder of this module.                  #
# ###############################################################################


from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.exceptions import UserError
from werkzeug.utils import redirect
from decimal import *

show_services = [
    "PurolatorExpress",
    "PurolatorExpress10:30AM",
    "PurolatorExpress12PM",
    "PurolatorExpress9AM",
    "PurolatorExpressBox",
    "PurolatorExpressBox10:30AM",
    "PurolatorExpressBox12PM",
    "PurolatorExpressBox9AM",
    "PurolatorExpressBoxEvening",
    "PurolatorExpressBoxInternational",
    "PurolatorExpressBoxU.S.",
    "PurolatorExpressEnvelope",
    "PurolatorExpressEnvelope10:30AM",
    "PurolatorExpressEnvelope12PM",
    "PurolatorExpressEnvelope9AM",
    "PurolatorExpressEnvelopeEvening",
    "PurolatorExpressEnvelopeInternational",
    "PurolatorExpressEnvelopeU.S.",
    "PurolatorExpressEvening",
    "PurolatorExpressInternational",
    "PurolatorExpressInternational10:30AM",
    "PurolatorExpressInternational12:00",
    "PurolatorExpressInternational10:30AM",
    "PurolatorExpressInternational9AM",
    "PurolatorExpressInternationalBox10:30AM",
    "PurolatorExpressInternationalBox12:00",
    "PurolatorExpressInternationalBox9AM",
    "PurolatorExpressInternationalEnvelope10:30AM",
    "PurolatorExpressInternationalEnvelope12:00",
    "PurolatorExpressInternationalEnvelope9AM",
    "PurolatorExpressInternationalPack10:30AM",
    "PurolatorExpressInternationalPack12:00",
    "PurolatorExpressInternationalPack9AM",
    "PurolatorExpressPack",
    "PurolatorExpressPack10:30AM",
    "PurolatorExpressPack12PM",
    "PurolatorExpressPack9AM",
    "PurolatorExpressPackEvening",
    "PurolatorExpressPackInternational",
    "PurolatorExpressPackU.S.",
    "PurolatorExpressU.S.",
    "PurolatorExpressU.S.10:30AM",
    "PurolatorExpressU.S.12:00",
    "PurolatorExpressU.S.9AM",
    "PurolatorExpressU.S.Box10:30AM",
    "PurolatorExpressU.S.Box12:00",
    "PurolatorExpressU.S.Box9AM",
    "PurolatorExpressU.S.Envelope10:30AM",
    "PurolatorExpressU.S.Envelope12:00",
    "PurolatorExpressU.S.Envelope9AM",
    "PurolatorExpressU.S.Pack10:30AM",
    "PurolatorExpressU.S.Pack12:00",
    "PurolatorExpressU.S.Pack9AM",
    "PurolatorGround",
    "PurolatorGround10:30AM",
    "PurolatorGround9AM",
    "PurolatorGroundDistribution",
    "PurolatorGroundEvening",
    "PurolatorGroundRegional",
    "PurolatorGroundU.S.",
    "PurolatorQuickShip",
    "PurolatorQuickShipBox",
    "PurolatorQuickShipEnvelope",
    "PurolatorQuickShipPack",
]


class WebsiteSaleDeliveryInheritPurolator(Delivery):

    # @http.route(
    #     ["/carrier/detail"],
    #     type="json",
    #     auth="public",
    #     methods=["POST"],
    #     website=True,
    #     csrf=False,
    # )
    # def get_carrier_delivery_type(self, **post):
    #     carrier_id = int(post["carrier_id"])
    #
    #     carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
    #     print(carrier.delivery_type)
    #     res = {}
    #     res["delivery_type"] = carrier.delivery_type
    #     return res



    # For Delivery Purolator
    @http.route(
        ["/carrier/detail/purolator"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def get_carrier_delivery_type_purolator(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post["carrier_id"])
        res = {}
        # carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
        purolator_service_rates = []
        minimum_rate = 0

        choice = (
            request.env["choose.delivery.carrier"]
            .sudo()
            .search(
                [
                    ("order_id", "=", order.id),
                    ("carrier_id", "=", carrier_id),
                ],
                order="id desc",
                limit=1,
            )
        )
        purolator_service_type = (
            request.env["purolator.service"]
            .sudo()
            .search([("choise_id", "=", choice.id), ("active", "=", True)])
        )
        select_service = False
        if purolator_service_type:
            minimum_rate = purolator_service_type[0].total_price
            for record in purolator_service_type:
                if record.service_id in show_services:
                    if record.total_price < minimum_rate:
                        minimum_rate = record.total_price
                        select_service = record.id
                    name = (
                        record.service_id
                        + ",Shipping Cost: \n "
                        + str(record.total_price)
                        + ",\n Expected Delivery Date: "
                        + str(record.expected_delivery_date)
                    )
                    purolator_service_rates.append(
                        {
                            "value": record.id,
                            "name": name,
                            "total_price": record.total_price,
                            "service_id": record.service_id,
                            "shipment_date": record.shipment_date,
                            "expected_delivery_date": record.expected_delivery_date,
                            "expected_transit_days": record.expected_transit_days,
                            "base_price": record.base_price,
                            "surcharges": record.surcharges,
                            "taxes": record.taxes,
                            "options": record.options,
                            "total_price": record.total_price,
                            "order_id": record.order_id.id,
                            "choise_id": record.choise_id.id,
                        }
                    )
        update_delivery_line = order.update_delivery_line_purolator(select_service)
        res["purolator_service_rates"] = purolator_service_rates

        return res



    @http.route(
        ["/shop/update_carrier/purolator"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def update_eshop_carrier_purolator(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post["carrier_id"])
        carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
        if order and carrier_id != order.carrier_id.id:
            if any(
                tx.state not in ("canceled", "error", "draft")
                for tx in order.transaction_ids
            ):
                raise UserError(
                    _(
                        "It seems that there is already a transaction for your order, you can not change the delivery method anymore"
                    )
                )
            order._check_carrier_quotation(force_carrier_id=carrier_id)

        print(order.amount_total)
        order.update_delivery_line_purolator(service_id=post["service_id"])
        print(order.amount_total)
        return self._update_website_sale_delivery_return(order, **post)



    # @http.route(
    #     ["/shop/update_carrier"],
    #     type="json",
    #     auth="public",
    #     methods=["POST"],
    #     website=True,
    #     csrf=False,
    # )
    # def update_eshop_carrier(self, **post):
    #     order = request.website.sale_get_order()
    #     carrier_id = int(post["carrier_id"])

    #     carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
    #     if carrier.delivery_type != "purolator":
    #         return super().update_eshop_carrier(self, **post)

    #     if order:
    #         order._check_carrier_quotation(force_carrier_id=carrier_id)
    #     service_id = ""

    #     # For Delivery Purolator
    #     purolator_service_rates = []
    #     minimum_rate = 0
    #     if carrier.delivery_type == "purolator":
    #         choice = (
    #             request.env["choose.delivery.carrier"]
    #             .sudo()
    #             .search(
    #                 [
    #                     ("order_id", "=", order.id),
    #                     ("carrier_id", "=", order.carrier_id.id),
    #                 ],
    #                 order="id desc",
    #                 limit=1,
    #             )
    #         )
    #         purolator_service_type = (
    #             request.env["purolator.service"]
    #             .sudo()
    #             .search([("choise_id", "=", choice.id), ("active", "=", True)])
    #         )
    #         select_service = False
    #         if purolator_service_type:
    #             minimum_rate = purolator_service_type[0].total_price
    #             for record in purolator_service_type:
    #                 if record.service_id in show_services:
    #                     if record.total_price < minimum_rate:
    #                         minimum_rate = record.total_price
    #                         select_service = record.id
    #                     name = (
    #                         record.service_id
    #                         + ",Shipping Cost: \n "
    #                         + str(record.total_price)
    #                         + ",\n Expected Delivery Date: "
    #                         + str(record.expected_delivery_date)
    #                     )
    #                     purolator_service_rates.append(
    #                         {
    #                             "value": record.id,
    #                             "name": name,
    #                             "total_price": record.total_price,
    #                             "service_id": record.service_id,
    #                             "shipment_date": record.shipment_date,
    #                             "expected_delivery_date": record.expected_delivery_date,
    #                             "expected_transit_days": record.expected_transit_days,
    #                             "base_price": record.base_price,
    #                             "surcharges": record.surcharges,
    #                             "taxes": record.taxes,
    #                             "options": record.options,
    #                             "total_price": record.total_price,
    #                             "order_id": record.order_id.id,
    #                             "choise_id": record.choise_id.id,
    #                         }
    #                     )
    #         update_delivery_line = order.update_delivery_line(select_service)
    #     post["purolator_service_rates"] = purolator_service_rates
    #     delivery_line = order.order_line.filtered("is_delivery")
    #     for service in (
    #         request.env["purolator.service"]
    #         .sudo()
    #         .search([("order_id", "=", order.id)])
    #     ):
    #         if service.total_price == delivery_line.price_subtotal:
    #             service_id = service.id
    #     post["service_id"] = service_id
    #     return self._update_website_sale_delivery_return(order, **post)

    @http.route(
        ["/shop/carrier_rate_shipment/purolator"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_carrier_rate_shipment_purolator(self, carrier_id, **kw):
        carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
        if carrier.delivery_type != "purolator":
            return super().cart_carrier_rate_shipment(carrier_id=carrier_id)
        order = request.website.sale_get_order(force_create=True)
        assert int(carrier_id) in order._get_delivery_methods().ids, "unallowed carrier"
        Monetary = request.env["ir.qweb.field.monetary"]
        res = {"carrier_id": carrier_id}
        rate = carrier.rate_shipment(order)
        purolator_service_rates = []
        service_id = ""
        minimum_rate = 0
        if carrier.delivery_type == "purolator":
            purolator_service_type = (
                request.env["purolator.service"]
                .sudo()
                .search([("order_id", "=", order.id)])
            )
            if purolator_service_type:
                minimum_rate = purolator_service_type[0].total_price
                for record in purolator_service_type:
                    name = (
                        record.service_id
                        + ", Shipping Cost: "
                        + str(record.total_price)
                        + ", Expected Delivery Date: "
                        + str(record.expected_delivery_date)
                    )
                    purolator_service_rates.append({"value": record.id, "name": name})
                    if record.service_id in show_services:
                        if record.total_price < minimum_rate:
                            minimum_rate = record.total_price
                            service_id = record.id
                        # update_delivery_line = order.update_delivery_line_purolator(service_id)

        ShipmentEstimate = rate.get("ShipmentEstimate")
        # if ShipmentEstimate != None:
        #     ShipmentEstimate = self.process_rate_purolator(ShipmentEstimate, order)
        if rate.get("success"):
            res["status"] = True
            res["new_amount_delivery"] = Monetary.value_to_html(
                minimum_rate, {"display_currency": order.currency_id}
            )
            res["is_free_delivery"] = not bool(minimum_rate)
            res["error_message"] = rate["warning_message"]
            res["service_id"] = str(service_id)
            res["ShipmentEstimate"] = rate.get("ShipmentEstimate")
            res["purolator_service_type"] = purolator_service_rates
            res["free_delivery"] = rate.get("free_delivery")
        else:
            res["status"] = False
            res["new_amount_delivery"] = Monetary.value_to_html(
                0.0, {"display_currency": order.currency_id}
            )
            res["error_message"] = rate["error_message"]
            res["ShipmentEstimate"] = []
            res["purolator_service_type"] = purolator_service_rates
            res["service_id"] = str(service_id)
        return res



    # def _update_website_sale_delivery_return(self, order, **post):
    #     Monetary = request.env["ir.qweb.field.monetary"]
    #     carrier_id = int(post["carrier_id"])
    #     carrier = (
    #         request.env["delivery.carrier"].sudo().search([("id", "=", carrier_id)])
    #     )
    #     if carrier.delivery_type != "purolator":
    #         return super()._update_website_sale_delivery_return(order, **post)
    #     currency = order.currency_id
    #     carrier = (
    #         request.env["delivery.carrier"].sudo().search([("id", "=", carrier_id)])
    #     )
    #     free_delivery = False
    #     if carrier and carrier.delivery_type == "purolator":
    #         if (
    #             post.get("purolator_service_rates")
    #             and carrier.free_over
    #             and order._compute_amount_total_without_delivery() >= carrier.amount
    #         ):
    #             print("FREE SHIPMENT")
    #             order.amount_delivery = 0.0
    #             order._remove_delivery_line()
    #             free_delivery = True

    #     if order:
    #         return {
    #             "status": order.delivery_rating_success,
    #             "error_message": order.delivery_message,
    #             "carrier_id": carrier_id,
    #             "is_free_delivery": not bool(order.amount_delivery),
    #             "new_amount_delivery": Monetary.value_to_html(
    #                 order.amount_delivery, {"display_currency": currency}
    #             ),
    #             "new_amount_untaxed": Monetary.value_to_html(
    #                 order.amount_untaxed, {"display_currency": currency}
    #             ),
    #             "new_amount_tax": Monetary.value_to_html(
    #                 order.amount_tax, {"display_currency": currency}
    #             ),
    #             "new_amount_total": Monetary.value_to_html(
    #                 order.amount_total, {"display_currency": currency}
    #             ),
    #             "purolator_service_rates": post["purolator_service_rates"],
    #             "service_id": post["service_id"],
    #             "free_delivery": free_delivery,
    #         }
    #     return {}

    # @http.route(
    #     ["/shop/update_carrier_service"],
    #     type="json",
    #     auth="public",
    #     methods=["POST"],
    #     website=True,
    #     csrf=False,
    # )
    # def get_total_price(self, **post):
    #     order = request.website.sale_get_order()
    #     Monetary = request.env["ir.qweb.field.monetary"]
    #     currency = order.currency_id
    #     update_delivery_line = order.update_delivery_line(post["service_id"])
    #     if post and update_delivery_line["status"] == True:
    #         data = {
    #             "status": True,
    #             "new_amount_delivery": Monetary.value_to_html(
    #                 update_delivery_line["new_service_rate"],
    #                 {"display_currency": currency},
    #             ),
    #             "new_amount_untaxed": Monetary.value_to_html(
    #                 order.amount_untaxed, {"display_currency": currency}
    #             ),
    #             "new_amount_tax": Monetary.value_to_html(
    #                 order.amount_tax, {"display_currency": currency}
    #             ),
    #             "new_amount_total": Monetary.value_to_html(
    #                 order.amount_total, {"display_currency": currency}
    #             ),
    #         }
    #     else:
    #         data = {
    #             "status": False,
    #             "new_amount_delivery": Monetary.value_to_html(
    #                 0, {"display_currency": currency}
    #             ),
    #             "new_amount_untaxed": Monetary.value_to_html(
    #                 0, {"display_currency": currency}
    #             ),
    #             "new_amount_tax": Monetary.value_to_html(
    #                 0, {"display_currency": currency}
    #             ),
    #             "new_amount_total": Monetary.value_to_html(
    #                 0, {"display_currency": currency}
    #             ),
    #         }
    #     return
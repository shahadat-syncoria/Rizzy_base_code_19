# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import http, _
from odoo.http import request
from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.exceptions import UserError
from decimal import *


class WebsiteSaleDeliveryInheritCanadaPost(Delivery):
    @http.route(
        ["/shop/update_carrier/canadapost"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def update_eshop_carrier_canadapost(self, **post):
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

        order.update_delivery_line_canadapost(service_code=post["service_id"])
        return self._update_website_sale_delivery_return(order, **post)

    @http.route(
        ["/shop/carrier_rate_shipment/canadapost"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
    )
    def cart_carrier_rate_shipment_canadapost(self, carrier_id, **kw):
        carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
        if carrier.delivery_type != "canadapost":
            return super().cart_carrier_rate_shipment(carrier_id=carrier_id)
        order = request.website.sale_get_order(force_create=True)
        assert int(carrier_id) in order._get_delivery_methods().ids, "unallowed carrier"
        Monetary = request.env["ir.qweb.field.monetary"]
        res = {"carrier_id": carrier_id}
        rate = carrier.rate_shipment(order)
        cnpost_service_rates = []
        service_code, minimum_rate = "", 0
        if carrier.delivery_type == "canadapost":
            cnpost_service_type = (
                request.env["canadapost.service"]
                .sudo()
                .search([("order_id", "=", order.id)])
            )
            if cnpost_service_type:
                service_code = cnpost_service_type[0].id
                minimum_rate = cnpost_service_type[0].total_price
                for record in cnpost_service_type:
                    name = (
                            record.service_code
                            + ", Shipping Cost: "
                            + str(record.total_price)
                            + ", Expected Delivery Date: "
                            + str(record.expected_delivery_date)
                    )
                    cnpost_service_rates.append({"value": record.id, "name": name})
                    if record.total_price < minimum_rate:
                        minimum_rate, service_code = record.total_price, record.id
                    # update_delivery_line = order.update_delivery_line_canadapost(service_code)

        ShipmentEstimate = rate.get("ShipmentEstimate")

        if rate.get("success"):
            res["status"] = True
            res["new_amount_delivery"] = Monetary.value_to_html(
                minimum_rate, {"display_currency": order.currency_id}
            )
            res["is_free_delivery"] = not bool(minimum_rate)
            res["error_message"] = rate["warning_message"]
            res["service_code"] = str(service_code)
            res["ShipmentEstimate"] = rate.get("ShipmentEstimate")
            res["cnpost_service_type"] = cnpost_service_rates
            res["free_delivery"] = rate.get("free_delivery")
        else:
            res["status"] = False
            res["new_amount_delivery"] = Monetary.value_to_html(
                0.0, {"display_currency": order.currency_id}
            )
            res["error_message"] = rate["error_message"]
            res["ShipmentEstimate"] = []
            res["cnpost_service_type"] = cnpost_service_rates
            res["service_code"] = str(service_code)
        return res

    @http.route(
        ["/carrier/detail/canadapost"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def get_carrier_delivery_type_canadapost(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post["carrier_id"])
        res = {}
        cnpost_service_rates = []
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
        cnpost_service_type = (
            request.env["canadapost.service"]
            .sudo()
            .search([("choise_id", "=", choice.id), ("active", "=", True)])
        )
        select_service = False
        if cnpost_service_type:
            minimum_rate = cnpost_service_type[0].total_price
            for record in cnpost_service_type:
                if record.total_price < minimum_rate:
                    minimum_rate = record.total_price
                name = (
                        record.service_code
                        + ",Shipping Cost: \n "
                        + str(record.total_price)
                        + ",\n Expected Delivery Date: "
                        + str(record.expected_delivery_date)
                )
                cnpost_service_rates.append(
                    {
                        "value": record.id,
                        "name": name,
                        "total_price": record.total_price,
                        "service_code": record.service_code,
                        "service_name": record.service_name,
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
        res["cnpost_service_rates"] = cnpost_service_rates
        return res

    @http.route(
        ["/carrier/detail/canadapost"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def get_carrier_delivery_type_canadapost(self, **post):
        order = request.website.sale_get_order()
        carrier_id = int(post["carrier_id"])
        res = {}
        cnpost_service_rates = []
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
        cnpost_service_type = (
            request.env["canadapost.service"]
            .sudo()
            .search([("choise_id", "=", choice.id), ("active", "=", True)])
        )
        select_service = False
        if cnpost_service_type:
            minimum_rate = cnpost_service_type[0].total_price
            for record in cnpost_service_type:
                if record.total_price < minimum_rate:
                    minimum_rate = record.total_price
                name = (
                        record.service_code
                        + ",Shipping Cost: \n "
                        + str(record.total_price)
                        + ",\n Expected Delivery Date: "
                        + str(record.expected_delivery_date)
                )
                cnpost_service_rates.append(
                    {
                        "value": record.id,
                        "name": name,
                        "total_price": record.total_price,
                        "service_code": record.service_code,
                        "service_name": record.service_name,
                        "service_id": record.id,
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
        res["cnpost_service_rates"] = cnpost_service_rates
        return res

#     ["/carrier/detail"],
#     type="json",
#     auth="public",
#     methods=["POST"],
#     website=True,
#     csrf=False,
# )
# def get_carrier_delivery_type(self, **post):
#     carrier_id = int(post["carrier_id"])

#     carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
#     print(carrier.delivery_type)
#     res = {}
#     res["delivery_type"] = carrier.delivery_type
#     return res

# @http.route(
#     ["/carrier/detail/canadapost"],
#     type="json",
#     auth="public",
#     methods=["POST"],
#     website=True,
#     csrf=False,
# )
# def get_carrier_delivery_type_canadapost(self, **post):
#     order = request.website.sale_get_order()
#     carrier_id = int(post["carrier_id"])
#     res = {}
#     cnpost_service_rates = []
#     minimum_rate = 0
#     choice = (
#         request.env["choose.delivery.carrier"]
#         .sudo()
#         .search(
#             [
#                 ("order_id", "=", order.id),
#                 ("carrier_id", "=", carrier_id),
#             ],
#             order="id desc",
#             limit=1,
#         )
#     )
#     cnpost_service_type = (
#         request.env["canadapost.service"]
#         .sudo()
#         .search([("choise_id", "=", choice.id), ("active", "=", True)])
#     )
#     select_service = False
#     if cnpost_service_type:
#         minimum_rate = cnpost_service_type[0].total_price
#         for record in cnpost_service_type:
#             if record.total_price < minimum_rate:
#                 minimum_rate = record.total_price
#             name = (
#                 record.service_code
#                 + ",Shipping Cost: \n "
#                 + str(record.total_price)
#                 + ",\n Expected Delivery Date: "
#                 + str(record.expected_delivery_date)
#             )
#             cnpost_service_rates.append(
#                 {
#                     "value": record.id,
#                     "name": name,
#                     "total_price": record.total_price,
#                     "service_code": record.service_code,
#                     "service_name": record.service_name,
#                     "shipment_date": record.shipment_date,
#                     "expected_delivery_date": record.expected_delivery_date,
#                     "expected_transit_days": record.expected_transit_days,
#                     "base_price": record.base_price,
#                     "surcharges": record.surcharges,
#                     "taxes": record.taxes,
#                     "options": record.options,
#                     "total_price": record.total_price,
#                     "order_id": record.order_id.id,
#                     "choise_id": record.choise_id.id,
#                 }
#             )
#     res["cnpost_service_rates"] = cnpost_service_rates
#     return res

# @http.route(
#     ["/shop/update_carrier/canadapost"],
#     type="json",
#     auth="public",
#     methods=["POST"],
#     website=True,
#     csrf=False,
# )
# def update_eshop_carrier_canadapost(self, **post):
#     order = request.website.sale_get_order()
#     carrier_id = int(post["carrier_id"])
#     carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
#     if order and carrier_id != order.carrier_id.id:
#         if any(
#             tx.state not in ("canceled", "error", "draft")
#             for tx in order.transaction_ids
#         ):
#             raise UserError(
#                 _(
#                     "It seems that there is already a transaction for your order, you can not change the delivery method anymore"
#                 )
#             )
#         order._check_carrier_quotation(force_carrier_id=carrier_id)

#     print(order.amount_total)
#     order.amount_delivery = post["amount_delivery"]
#     print(order.amount_total)
#     return self._update_website_sale_delivery_return(order, **post)


#     @http.route(
#         ["/shop/update_carrier"],
#         type="json",
#         auth="public",
#         methods=["POST"],
#         website=True,
#         csrf=False,
#     )
#     def update_eshop_carrier(self, **post):
#         order = request.website.sale_get_order()
#         carrier_id = int(post["carrier_id"])
#         carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
#         if carrier.delivery_type != "canadapost":
#             return super().update_eshop_carrier(**post)
#         if order:
#             order._check_carrier_quotation(force_carrier_id=carrier_id)
#         service_code = ""
#         cnpost_service_rates = []
#         minimum_rate = 0
#         if carrier.delivery_type == "canadapost":
#             choice = (
#                 request.env["choose.delivery.carrier"]
#                 .sudo()
#                 .search(
#                     [
#                         ("order_id", "=", order.id),
#                         ("carrier_id", "=", order.carrier_id.id),
#                     ],
#                     order="id desc",
#                     limit=1,
#                 )
#             )
#             cnpost_service_type = (
#                 request.env["canadapost.service"]
#                 .sudo()
#                 .search([("choise_id", "=", choice.id), ("active", "=", True)])
#             )
#             select_service = False
#             if cnpost_service_type:
#                 minimum_rate, select_service = (
#                     cnpost_service_type[0].total_price,
#                     cnpost_service_type[0].id,
#                 )
#                 for record in cnpost_service_type:
#                     if record.total_price < minimum_rate:
#                         minimum_rate, select_service = record.total_price, record.id
#                     name = (
#                         record.service_code
#                         + ",Shipping Cost: \n "
#                         + str(record.total_price)
#                         + ",\n Expected Delivery Date: "
#                         + str(record.expected_delivery_date)
#                     )
#                     cnpost_service_rates.append(
#                         {
#                             "value": record.id,
#                             "name": name,
#                             "total_price": record.total_price,
#                             "service_code": record.service_code,
#                             "service_name": record.service_name,
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
#             print(select_service)
#             update_delivery_line = order.update_delivery_line(select_service)
#         post["cnpost_service_rates"] = cnpost_service_rates
#         delivery_line = order.order_line.filtered("is_delivery")
#         for service in (
#             request.env["canadapost.service"]
#             .sudo()
#             .search([("order_id", "=", order.id)])
#         ):
#             if service.total_price == delivery_line.price_subtotal:
#                 service_code = service.id
#         post["service_code"] = service_code
#         return self._update_website_sale_delivery_return(order, **post)

#     @http.route(
#         ["/shop/carrier_rate_shipment"],
#         type="json",
#         auth="public",
#         methods=["POST"],
#         website=True,
#     )
#     def cart_carrier_rate_shipment(self, carrier_id, **kw):
#         carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
#         if carrier.delivery_type != "canadapost":
#             return super().cart_carrier_rate_shipment(carrier_id=carrier_id)
#         order = request.website.sale_get_order(force_create=True)
#         assert int(carrier_id) in order._get_delivery_methods().ids, "unallowed carrier"
#         Monetary = request.env["ir.qweb.field.monetary"]
#         res = {"carrier_id": carrier_id}
#         rate = carrier.rate_shipment(order)
#         cnpost_service_rates = []
#         service_code, minimum_rate = "", 0
#         if carrier.delivery_type == "canadapost":
#             cnpost_service_type = (
#                 request.env["canadapost.service"]
#                 .sudo()
#                 .search([("order_id", "=", order.id)])
#             )
#             if cnpost_service_type:
#                 service_code = cnpost_service_type[0].id
#                 minimum_rate = cnpost_service_type[0].total_price
#                 for record in cnpost_service_type:
#                     name = (
#                         record.service_code
#                         + ", Shipping Cost: "
#                         + str(record.total_price)
#                         + ", Expected Delivery Date: "
#                         + str(record.expected_delivery_date)
#                     )
#                     cnpost_service_rates.append({"value": record.id, "name": name})
#                     if record.total_price < minimum_rate:
#                         minimum_rate, service_code = record.total_price, record.id
#                     update_delivery_line = order.update_delivery_line(service_code)

#         ShipmentEstimate = rate.get("ShipmentEstimate")

#         if rate.get("success"):
#             res["status"] = True
#             res["new_amount_delivery"] = Monetary.value_to_html(
#                 minimum_rate, {"display_currency": order.currency_id}
#             )
#             res["is_free_delivery"] = not bool(minimum_rate)
#             res["error_message"] = rate["warning_message"]
#             res["service_code"] = str(service_code)
#             res["ShipmentEstimate"] = rate.get("ShipmentEstimate")
#             res["cnpost_service_type"] = cnpost_service_rates
#             res["free_delivery"] = rate.get("free_delivery")
#         else:
#             res["status"] = False
#             res["new_amount_delivery"] = Monetary.value_to_html(
#                 0.0, {"display_currency": order.currency_id}
#             )
#             res["error_message"] = rate["error_message"]
#             res["ShipmentEstimate"] = []
#             res["cnpost_service_type"] = cnpost_service_rates
#             res["service_code"] = str(service_code)
#         return res

#     def _update_website_sale_delivery_return(self, order, **post):
#         carrier_id = int(post["carrier_id"])
#         carrier = (
#             request.env["delivery.carrier"].sudo().search([("id", "=", carrier_id)])
#         )
#         if carrier.delivery_type != "canadapost":
#             return super()._update_website_sale_delivery_return(order, **post)
#         Monetary = request.env["ir.qweb.field.monetary"]
#         currency = order.currency_id
#         free_delivery = False
#         if carrier and carrier.delivery_type == "canadapost":
#             if (
#                 post.get("cnpost_service_rates")
#                 and carrier.free_over
#                 and order._compute_amount_total_without_delivery() >= carrier.amount
#             ):
#                 print("FREE SHIPMENT")
#                 order.amount_delivery = 0.0
#                 order._remove_delivery_line()
#                 free_delivery = True

#         if order:
#             return {
#                 "status": order.delivery_rating_success,
#                 "error_message": order.delivery_message,
#                 "carrier_id": carrier_id,
#                 "is_free_delivery": not bool(order.amount_delivery),
#                 "new_amount_delivery": Monetary.value_to_html(
#                     order.amount_delivery, {"display_currency": currency}
#                 ),
#                 "new_amount_untaxed": Monetary.value_to_html(
#                     order.amount_untaxed, {"display_currency": currency}
#                 ),
#                 "new_amount_tax": Monetary.value_to_html(
#                     order.amount_tax, {"display_currency": currency}
#                 ),
#                 "new_amount_total": Monetary.value_to_html(
#                     order.amount_total, {"display_currency": currency}
#                 ),
#                 "cnpost_service_rates": post["cnpost_service_rates"],
#                 "service_code": post["service_code"],
#                 "free_delivery": free_delivery,
#             }
#         return {}

#     @http.route(
#         ["/shop/update_carrier_service"],
#         type="json",
#         auth="public",
#         methods=["POST"],
#         website=True,
#         csrf=False,
#     )
#     def get_total_price(self, **post):
#         order = request.website.sale_get_order()
#         Monetary = request.env["ir.qweb.field.monetary"]
#         currency = order.currency_id
#         update_delivery_line = order.update_delivery_line(post["service_code"])
#         if post and update_delivery_line["status"] == True:
#             data = {
#                 "status": True,
#                 "new_amount_delivery": Monetary.value_to_html(
#                     update_delivery_line["new_service_rate"],
#                     {"display_currency": currency},
#                 ),
#                 "new_amount_untaxed": Monetary.value_to_html(
#                     order.amount_untaxed, {"display_currency": currency}
#                 ),
#                 "new_amount_tax": Monetary.value_to_html(
#                     order.amount_tax, {"display_currency": currency}
#                 ),
#                 "new_amount_total": Monetary.value_to_html(
#                     order.amount_total, {"display_currency": currency}
#                 ),
#             }
#         else:
#             data = {
#                 "status": False,
#                 "new_amount_delivery": Monetary.value_to_html(
#                     0, {"display_currency": currency}
#                 ),
#                 "new_amount_untaxed": Monetary.value_to_html(
#                     0, {"display_currency": currency}
#                 ),
#                 "new_amount_tax": Monetary.value_to_html(
#                     0, {"display_currency": currency}
#                 ),
#                 "new_amount_total": Monetary.value_to_html(
#                     0, {"display_currency": currency}
#                 ),
#             }
#         return data

#     def process_rate_canadapost(self, datas, order):
#         Monetary = request.env["ir.qweb.field.monetary"]
#         if len(datas) > 0:
#             for data in datas:
#                 surcharges_total = Decimal("0.0")
#                 taxes_total = float(data.get("price-details").get("due")) - float(
#                     data.get("price-details").get("base")
#                 )
#                 options_total = Decimal("0.0")
#                 data["surcharges_total"] = Monetary.value_to_html(
#                     float(surcharges_total), {"display_currency": order.currency_id}
#                 )
#                 data["taxes_total"] = Monetary.value_to_html(
#                     float(taxes_total), {"display_currency": order.currency_id}
#                 )
#                 data["options_total"] = Monetary.value_to_html(
#                     float(options_total), {"display_currency": order.currency_id}
#                 )
#                 data["BasePrice"] = Monetary.value_to_html(
#                     float(data.get("price-details").get("base")),
#                     {"display_currency": order.currency_id},
#                 )
#                 data["TotalPrice"] = Monetary.value_to_html(
#                     float(data.get("price-details").get("due")),
#                     {"display_currency": order.currency_id},
#                 )
#         return datas

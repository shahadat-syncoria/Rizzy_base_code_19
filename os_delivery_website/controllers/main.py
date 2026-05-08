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


class WebsiteSaleDeliveryInheritCommon(Delivery):
    @http.route(
        ["/carrier/detail"],
        type="json",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=False,
    )
    def get_carrier_delivery_type(self, **post):
        carrier_id = int(post["carrier_id"])

        carrier = request.env["delivery.carrier"].sudo().browse(int(carrier_id))
        print(carrier.delivery_type)
        res = {}
        res["delivery_type"] = carrier.delivery_type
        return res

    @http.route(['/shop/get_delivery_rate'], type='json', auth='public', methods=['POST'], website=True)
    def shop_get_delivery_rate(self, dm_id):
        order = request.website.sale_get_order(force_create=True)

        if not int(dm_id) in order._get_delivery_methods().ids:
            raise UserError(
                _('It seems that a delivery method is not compatible with your address. Please refresh the page and try again.'))

        Monetary = request.env['ir.qweb.field.monetary']

        res = {'carrier_id': dm_id}
        carrier = request.env['delivery.carrier'].sudo().browse(int(dm_id))
        if carrier.delivery_type == 'purolator' or carrier.delivery_type == 'canadapost':
            return res
        else:
            return super().shop_get_delivery_rate(dm_id)

    # @http.route(['/shop/update_carrier'], type='json', auth='public', methods=['POST'], website=True, csrf=False)
    # def update_eshop_carrier(self, **post):
    #     order = request.website.sale_get_order()
    #     carrier_id = int(post['carrier_id'])
    #     carrier = request.env['delivery.carrier'].sudo().browse(carrier_id)
    #     if carrier.delivery_type == 'purolator' or carrier.delivery_type == 'canadapost':
    #         return self._update_website_sale_delivery_return(order, **post)
    #
    #     return super(WebsiteSaleDeliveryInheritCommon, self).update_eshop_carrier(**post)



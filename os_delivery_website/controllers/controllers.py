# -*- coding: utf-8 -*-
# from odoo import http


# class OsDeliveryWebsite(http.Controller):
#     @http.route('/os_delivery_website/os_delivery_website', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/os_delivery_website/os_delivery_website/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('os_delivery_website.listing', {
#             'root': '/os_delivery_website/os_delivery_website',
#             'objects': http.request.env['os_delivery_website.os_delivery_website'].search([]),
#         })

#     @http.route('/os_delivery_website/os_delivery_website/objects/<model("os_delivery_website.os_delivery_website"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('os_delivery_website.object', {
#             'object': obj
#         })

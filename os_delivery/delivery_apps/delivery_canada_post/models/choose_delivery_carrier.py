# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, models, fields, _


class Providercanadapost(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    canadapost_shipping_date = fields.Date(default=fields.Date.today())
    canadapost_service = fields.Char()
    canadapost_service_type = fields.Many2one(comodel_name="canadapost.service")

    @api.onchange("canadapost_service_type")
    def onchange_canadapost_service_type(self):
        self.delivery_price = self.canadapost_service_type.total_price
        self.display_price = self.canadapost_service_type.total_price
        self.order_id.sudo().write({
            'canadapost_service': self.canadapost_service_type.service_code
        })

    @api.onchange("carrier_id")
    def onchange_canadapost_carrier_id(self):
        sers = self.env['canadapost.service'].sudo().search([])
        for ser in sers:
            ser.sudo().write({'active': False})



class CanadapostService(models.TransientModel):
    _name = "canadapost.service"
    _description = "Canada Post Services"

    service_name = fields.Char()
    service_code = fields.Char()
    service_link = fields.Char()
    shipment_date = fields.Date()
    expected_delivery_date = fields.Date()
    expected_transit_days = fields.Integer()
    surcharges = fields.Float()
    taxes = fields.Float()
    options = fields.Float(string="Optional")
    base_price = fields.Float()
    total_price = fields.Float(string="Display Price")
    order_id = fields.Many2one('sale.order')
    choise_id = fields.Many2one('choose.delivery.carrier')
    active = fields.Boolean(string='Status', default=True)

    # def name_get(self):
    #     res = []
    #     for record in self:
    #         name = record.service_name + ', Shipping Cost: ' + \
    #             str(record.total_price) + ', Expected Delivery Date: ' + \
    #             str(record.expected_delivery_date)
    #         res.append((record.id,  name))
    #     return res

    @api.depends('service_name')
    def _compute_display_name(self):
        for rec in self:
            name = rec.service_name + ', Shipping Cost: ' + \
                   str(rec.total_price) + ', Expected Delivery Date: ' + \
                   str(rec.expected_delivery_date)
            rec.display_name = name

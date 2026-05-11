# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import api, models, fields, _, tools
import logging

_logger = logging.getLogger(__name__)

class ProviderPurolator(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    purolator_shipping_date =  fields.Date(string='Shipping Date', required=True, default=fields.Date.today()) 
    purolator_total_weight =  fields.Float(string='Total Weight')
    purolator_weight_unit = fields.Selection([('LB', 'LB'), ('KG', 'KG')], default='KG', string="Weight Unit", required=True) 
    purolator_service = fields.Char()
    purolator_service_type = fields.Many2one(comodel_name="purolator.service")
    purolator_get_service = fields.Boolean(string='Select Service Options')
      
    @api.onchange("purolator_service")
    def onchange_purolator_service(self):
        return {'domain': {'purolator_service_type': [('choise_id','=',self.id), ('active','=',True)]}}

    @api.onchange("purolator_service_type")
    def onchange_my_selection_id(self):
        self.delivery_price = self.purolator_service_type.total_price
        self.display_price = self.purolator_service_type.total_price
        self.purolator_service = self.purolator_service_type.service_id
        self.order_id.purolator_service = self.purolator_service_type.service_id
        # TO DO: Update Sale Order
        #  Add Field in Sale Order
        order_total = 0
        for line in self.order_id.order_line:
            if not line.is_delivery:
                order_total += line.price_subtotal

        if self.carrier_id.free_over and order_total > self.carrier_id.amount:
            self.delivery_price = 0
            self.display_price = 0


    @api.onchange("carrier_id")
    def onchange_purolator_carrier_id(self):
        sers = self.env['purolator.service'].sudo().search([])
        total_weight = 0
        if self.carrier_id.delivery_type == 'purolator' and self.order_id:
            for line in self.order_id.order_line:
                total_weight += line.product_uom_qty*line.product_id.weight
        self.purolator_total_weight = total_weight
        for ser in sers:
            ser.sudo().write({'active':False})
        
           
class PurolatorService(models.TransientModel):
    _name = "purolator.service"
    _description = "Purolator Services"

    service_id = fields.Char(string="Service ID")
    shipment_date =  fields.Date()  
    expected_delivery_date =  fields.Date()
    expected_transit_days =  fields.Integer()
    surcharges = fields.Float()   
    taxes = fields.Float() 
    options = fields.Float(string="Optional") 
    base_price = fields.Float()  
    total_price = fields.Float(string="Display Price")   
    order_id = fields.Many2one('sale.order')
    choise_id = fields.Many2one('choose.delivery.carrier')
    active = fields.Boolean(string='Status', default=True)

    @api.depends('service_id')
    def _compute_display_name(self):
        for record in self:
            name = record.service_id + ', Shipping Cost: ' + str(record.total_price) + ', Expected Delivery Date: ' + str(record.expected_delivery_date)
            record.display_name = name

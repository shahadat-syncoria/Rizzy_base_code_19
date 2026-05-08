# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'   

    
    purolator_service = fields.Char()
    

    @api.model
    def update_delivery_line_purolator(self,service_id):
        for order in self:
            new_service_rate = 0
            for line in order.order_line:
                if line._is_delivery() == True:
                    service_id = self.env['purolator.service'].sudo().search(['|',('active','=',True),('active','=',False),('id','=',int(service_id))])
                    new_service_rate = service_id.total_price
                    line.price_unit = new_service_rate
            return {'status':True, 'new_service_rate':new_service_rate}

class ProductProduct(models.Model):
    _inherit = 'product.product'   

    country_of_manufacture = fields.Many2one('res.country', string='Country of Manufacture')

class ProductTemplate(models.Model):
    _inherit = 'product.template'   

    country_of_manufacture = fields.Many2one('res.country', string='Country of Manufacture')
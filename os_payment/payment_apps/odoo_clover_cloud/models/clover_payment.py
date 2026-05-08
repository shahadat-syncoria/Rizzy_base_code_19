# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging
import requests
import json

_logger = logging.getLogger(__name__)


class CloverPayment(models.Model):
    _name = 'clover.payment'
    _description = "Clover Payment"


    order_name = fields.Char()
    clover_order_id = fields.Char()
    clover_payment_id = fields.Char('External Payment Id')
    payment_status = fields.Char()
    move_id = fields.Many2one(
        string='Invoice',
        comodel_name='account.move',
        ondelete='restrict',
    )
    journal_id = fields.Many2one(
        string='Journal',
        comodel_name='account.journal',
        ondelete='restrict',
    )
    clover_payment_response =  fields.Text('Payment Response')


    @api.model
    def update_payment(self, values):
        try:
            self.write({'clover_payment_response': values})
        except Exception as e:
            _logger.warning(str(e.args))

    



    
        

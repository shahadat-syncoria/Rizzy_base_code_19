# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging
import requests
import json

_logger = logging.getLogger(__name__)



class CloverDevice(models.Model):
    _inherit = 'clover.device'

    method_id = fields.Many2one(
        string='Payment Method Id',
        comodel_name='pos.payment.method',
        ondelete='restrict',
        domain=[('use_payment_terminal','=','clover_cloud')],
    )


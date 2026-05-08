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
    _inherit = 'clover.payment'

    payment_method_id = fields.Many2one(
        string='Payment Method',
        comodel_name='pos.payment.method',
        ondelete='restrict',
    )
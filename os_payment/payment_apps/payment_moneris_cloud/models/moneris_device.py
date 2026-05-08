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



class MonerisDevice(models.Model):
    _name = 'moneris.device'
    _description = 'Moneris Device'
    _rec_name ='code'

    name = fields.Char("Device name")
    code = fields.Char("Device Code")
    journal_id = fields.Many2one(
        string='Journal Id',
        comodel_name='account.journal',
        ondelete='restrict',
        domain=[('use_cloud_terminal','=',True)],
    )
            

# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
import logging
logger = logging.getLogger(__name__)


class MarketplaceLogging(models.Model):
    _name = 'marketplace.logging'
    _description = """Marketplace Logging"""
    _order = 'id DESC'

    name = fields.Char(
        string='Name',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('marketpalce.logging'))

    create_uid = fields.Integer(string='Created by', required=True)
    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
    level = fields.Char(string='Level', required=True)
    summary = fields.Text(string='Summary', required=True)
    error = fields.Text(string='Error')
    type = fields.Selection(
        string='Type',
        selection=[('client', 'Client'), ('server', 'Server')]
    )
    model_name = fields.Char()

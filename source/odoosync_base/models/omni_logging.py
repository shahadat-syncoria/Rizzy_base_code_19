
# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, api, _


class OmniLogging(models.Model):
    _name = 'omni.logging'
    _description = 'Omni Logging'

    _rec_name = 'name'
    _order = 'name ASC'

    name = fields.Char(
        required=True,
        default=lambda self: _('New'),
        copy=False
    )
    create_uid = fields.Integer(string='Created by', required=True)
    log_platform = fields.Char()
    level = fields.Char(required=True)
    company_id = fields.Many2one(
        string="Company", comodel_name="res.company", ondelete="restrict", required=True
    )
    function = fields.Char()
    model = fields.Char()
    messages = fields.Text()
    error_messages = fields.Text()



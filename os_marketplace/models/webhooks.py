# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

# import logging
# import json
# from odoo import models, fields, api, exceptions, _
# from ast import literal_eval

# logger = logging.getLogger(__name__)


# class MarketplaceWebhooks(models.Model):
#     _name = 'marketplace.webhooks'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _description = 'Marketplace Webhooks'
#     _order = 'id desc'
#     _check_company_auto = True


#     name = fields.Char(
#         string='Name',
#         required=True,
#         copy=False,
#         readonly=True,
#         default=lambda self: self.env['ir.sequence'].next_by_code('marketplace.webhooks'))
#     company_id = fields.Many2one(
#         'res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
#     marketplace_instance_id = fields.Many2one(
#         string='Instance ID',
#         comodel_name='marketplace.instance',
#         ondelete='restrict',
#     )
#     marketplace_instance_type = fields.Selection(
#         related='marketplace_instance_id.marketplace_instance_type',
#         readonly=True,
#         store=True
#     )
#     state = fields.Selection(
#         string='state',
#         selection=[('draft', 'Draft'), ('connected', 'Connected')],
#         default='draft',
#     )


# class MarketplaceWebhooksConfig(models.Model):
#     _name = 'marketplace.webhooks.config'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _description = 'Marketplace Webhooks Config'
#     _order = 'id desc'
#     _check_company_auto = True

#     name = fields.Char(string='Name', required=True, copy=False,
#                        readonly=True, index=True, default=lambda self: _('New'))
#     company_id = fields.Many2one(
#         'res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
#     marketplace_instance_id = fields.Many2one(
#         string='Instance ID',
#         comodel_name='marketplace.instance',
#         ondelete='restrict',
#     )
#     marketplace_instance_type = fields.Selection(
#         related='marketplace_instance_id.marketplace_instance_type',
#         readonly=True,
#         store=True
#     )
#     state = fields.Selection(
#         string='state',
#         selection=[('draft', 'Draft'), ('connected', 'Connected'), ('disconnected', 'Disonnected')],
#         default='draft',
#     )

#     @api.model
#     def create(self, vals):
#         company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
#         self_comp = self.with_company(company_id)
#         if vals.get('name', 'New') == 'New':
#             vals['name'] = self.env['ir.sequence'].next_by_code('marketplace.webhooks.config') or 'New'
#         res = super(MarketplaceWebhooksConfig, self_comp).create(vals)
#         return res

#     def activate_webhooks(self):
#         if hasattr(self, '%s_activate_webhooks' % self.marketplace_instance_type):
#             return getattr(self, '%s_activate_webhooks' % self.marketplace_instance_type)()

#     def deactivate_webhooks(self):
#         if hasattr(self, '%s_deactivate_webhooks' % self.marketplace_instance_type):
#             return getattr(self, '%s_deactivate_webhooks' % self.marketplace_instance_type)()
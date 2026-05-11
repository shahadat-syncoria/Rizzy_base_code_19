# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, api, fields, tools, exceptions, _
from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")


class ProductProduct(models.Model):
    _inherit = 'product.product'

    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")


class ProductCateg(models.Model):
    _inherit = 'product.category'

    marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
    marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
#
#
# class ProductAttributeExtended(models.Model):
#     _inherit = 'product.attribute'
#
#     marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
#     marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
#
#
# class ProductAttributeValueExtended(models.Model):
#     _inherit = 'product.attribute.value'
#
#     marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
#     marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
#
#
# class PTAL(models.Model):
#     _inherit = 'product.template.attribute.line'
#
#     marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
#     marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
#
# class SCPQ(models.TransientModel):
#     _inherit = 'stock.change.product.qty'
#
#     marketplace_type = fields.Selection(related="marketplace_instance_id.marketplace_instance_type", string="Marketplace Type",store=True)
#     marketplace_instance_id = fields.Many2one("marketplace.instance", string="Marketplace Instance ID")
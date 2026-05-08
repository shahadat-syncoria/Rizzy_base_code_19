import json
import logging
import datetime
from odoo import fields, models, exceptions, _, api
from odoo.http import request
import re
import pprint
import time

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateVariantShopifyWizard(models.Model):
    _name = 'shopify.products.wiz'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model == "product.product":
            product_id = self.env["product.product"].browse(active_id)
            res["product_id"] = product_id
        elif active_model == "product.template":
            product_tpml_id = self.env["product.template"].browse(active_id)
            res["product_tpml_id"] = product_tpml_id

        return res

    shopify_instance_ids = fields.Many2many('marketplace.instance', string="Shopify Stores")
    product_id = fields.Many2one('product.product', 'Product')
    product_tpml_id = fields.Many2one('product.template', 'Product Template')
    note = fields.Char(compute='compute_note')




    def action_create(self):
        if self.product_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_shopify_instances(self.product_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id not in shopify_instance_already_created_list:
                    self.product_id.action_create_shopify_product(instance_obj)

        if self.product_tpml_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_template_shopify_instances(self.product_tpml_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id not in shopify_instance_already_created_list:
                    self.product_tpml_id.action_create_shopify_product(instance_obj)
        return

    @api.depends('product_id', 'product_tpml_id')
    def compute_note(self):
        result = ''
        # Product Product
        if self.product_id:
            mappings = self.env['shopify.product.mappings'].search([('product_id', '=', self.product_id.id)])
            if len(mappings) > 0:
                list_of_stores = []
                for i in mappings:
                    list_of_stores.append(i.shopify_instance_id.name)
                result += ', '.join(list_of_stores)
        # Product Template
        if self.product_tpml_id:
            mappings = self.env['shopify.product.mappings'].search(
                [('product_tmpl_id', '=', self.product_tpml_id.id)])
            if len(mappings) > 0:
                list_of_stores = []
                for i in mappings:
                    if i.shopify_instance_id.name not in list_of_stores:
                        list_of_stores.append(i.shopify_instance_id.name)
                result += ', '.join(list_of_stores)

        if len(result) > 0:
            self.note = 'Please notice that Product: %s already been created on Store(s): %s.' % (
            self.product_id.display_name or self.product_tpml_id.name, result)
        else:
            self.note = ''

    def get_product_shopify_instances(self, product_obj):
        result = []
        mappings = self.env['shopify.product.mappings'].search([('product_id', '=', product_obj.id)])
        if len(mappings) > 0:
            for store in mappings:
                result.append(store.shopify_instance_id.id)
        return result

    def get_product_template_shopify_instances(self, product_template_obj):
        result = []
        mappings = self.env['shopify.product.mappings'].search([('product_tmpl_id', '=', product_template_obj.id)])
        if len(mappings) > 0:
            for store in mappings:
                result.append(store.shopify_instance_id.id)
        return result

    def action_update(self):
        if self.product_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_shopify_instances(self.product_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id in shopify_instance_already_created_list:
                    self.product_id.action_update_shopify_product(instance_obj)

        if self.product_tpml_id and self.shopify_instance_ids:
            shopify_instance_already_created_list = self.get_product_template_shopify_instances(self.product_tpml_id)
            for instance_obj in self.shopify_instance_ids:
                if instance_obj.id in shopify_instance_already_created_list:
                    self.product_tpml_id.action_update_shopify_product(instance_obj)
        return


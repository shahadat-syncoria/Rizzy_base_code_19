# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import pprint
import re
from ..shopify.utils import *
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)
from odoo import exceptions


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shopify_id = fields.Char(string="Fulfillment ID", copy=False)
    shopify_order_id = fields.Char(string="Shopify Order ID", related='sale_id.shopify_id')
    shopify_status = fields.Char(copy=False, string='Shipment Status')
    shopify_service = fields.Char(copy=False, string='Shopify Service')
    shopify_track_updated = fields.Boolean(default=False, readonly=True, copy=False)
    shopify_tracking_urls = fields.Char(string="Shopify Tracking Url", copy=False)
    shopify_tracking_company = fields.Char(string="Shopify Tracking Company", copy=False)
    shopify_location_id = fields.Char(string='Shopify Location ID')
    shopify_tracking_number = fields.Char(string='Shopify Tracking Number')

    def get_fulfillment_order(self):
        for rec in self:
            marketplace_instance_id = rec.sale_id.marketplace_instance_id
            if not getattr(marketplace_instance_id, "use_graphql", False):
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            query = """
            query SyncoriaFulfillmentOrders($id: ID!) {
              order(id: $id) {
                fulfillmentOrders(first: 50) {
                  nodes {
                    id
                    status
                    assignedLocation { location { id } }
                    lineItems(first: 250) {
                      nodes {
                        id
                        lineItem { id legacyResourceId }
                      }
                    }
                  }
                }
              }
            }
            """
            fulfillment_orders, _next = self.env['marketplace.connector'].shopify_graphql_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url='/graphql.json',
                query=query,
                variables={"id": to_shopify_gid("Order", rec.sale_id.shopify_id)},
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
            )
            if fulfillment_orders.get('errors'):
                raise exceptions.UserError(_(fulfillment_orders.get('errors')))
            nodes = ((((fulfillment_orders.get("data") or {}).get("order") or {}).get("fulfillmentOrders") or {}).get("nodes") or [])
            normalized = []
            for node in nodes:
                normalized.append({
                    "id": node.get("id"),
                    "status": node.get("status"),
                    "assigned_location_id": int((((node.get("assignedLocation") or {}).get("location") or {}).get("id") or "0").split("/")[-1]),
                    "line_items": [
                        {
                            "id": li.get("id"),
                            "line_item_id": int(((li.get("lineItem") or {}).get("legacyResourceId") or 0)) if (li.get("lineItem") or {}).get("legacyResourceId") else None,
                        } for li in (((node.get("lineItems") or {}).get("nodes") or []))
                    ],
                })
            return {"fulfillment_orders": normalized}

    def create_shopify_fulfillment(self):
        for rec in self:
            shopify_instance_id = rec.sale_id.marketplace_instance_id
            shopify_warehouse_id = rec.location_id.shopify_warehouse_ids.filtered(lambda s: s.shopify_instance_id.id == shopify_instance_id.id)
            if not shopify_warehouse_id:
                raise exceptions.ValidationError('This location has not been mapped')
            res = rec.get_fulfillment_order()
            fulfillment_orders = res.get('fulfillment_orders')
            shopify_location_id = shopify_warehouse_id.shopify_invent_id
            """
                IF LOCATION MATCHES, THAT MEANS WE ARE FULFILLING FROM THE RIGHT LOCATION
                IF NOT, WE HAVE TO MOVE THE LOCATION
            """
            fulfillment_order = False
            fulfillable_orders = [order for order in fulfillment_orders if order['status'] in ('open', 'in_progress', 'scheduled')]
            for fulfillment in fulfillable_orders:

                if fulfillment['assigned_location_id'] == int(shopify_location_id):
                    fulfillment_order = fulfillment
                    break
            if not fulfillment_order:
                fulfillment_order = rec.move_shopify_fulfillment_order(fulfillable_orders, shopify_location_id)
            if fulfillment_order:
                fulfillment_order_id = fulfillment_order.get('id')
                line_items = fulfillment_order.get('line_items')
                line_map_dict = {}
                for line in line_items:
                    line_map_dict[str(line['line_item_id'])] = line['id']
                move_ids = rec.move_ids.filtered(lambda m: m.quantity > 0)
                fulfillment_order_line_items = []
                delivery_products = self.env['delivery.carrier'].search([]).product_id
                for move in move_ids:
                    if move.product_id in delivery_products:
                        continue
                    shopify_line_item_id = move.sale_line_id.shopify_id
                    fulfillment_order_line = {'id': line_map_dict.get(shopify_line_item_id),
                                              'quantity': int(move.quantity)}
                    fulfillment_order_line_items.append(fulfillment_order_line)
                if move_ids:
                    shipping_carrier_name = rec.carrier_id.shopify_carrier_name or rec.carrier_id.name
                    marketplace_instance_id = rec.sale_id.marketplace_instance_id
                    if not getattr(marketplace_instance_id, "use_graphql", False):
                        raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
                    mutation = """
                    mutation SyncoriaFulfillmentCreate($fulfillment: FulfillmentInput!, $notifyCustomer: Boolean) {
                      fulfillmentCreate(fulfillment: $fulfillment, notifyCustomer: $notifyCustomer) {
                        fulfillment { id }
                        userErrors { field message }
                      }
                    }
                    """
                    gql_payload = {
                        "lineItemsByFulfillmentOrder": [{
                            "fulfillmentOrderId": fulfillment_order_id,
                            "fulfillmentOrderLineItems": fulfillment_order_line_items,
                        }],
                        "trackingInfo": {
                            "number": rec.carrier_tracking_ref or rec.shopify_tracking_number or '',
                            "company": shipping_carrier_name,
                        },
                    }
                    fulfillment_res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers={'X-Service-Key': marketplace_instance_id.token},
                        url='/graphql.json',
                        query=mutation,
                        variables={"fulfillment": gql_payload, "notifyCustomer": True},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if not fulfillment_res.get('errors'):
                        fid = ((((fulfillment_res.get("data") or {}).get("fulfillmentCreate") or {}).get("fulfillment") or {}).get("id"))
                        fulfillment_res = {"fulfillment": {"id": fid.split("/")[-1] if fid else None}}
                    if fulfillment_res.get('errors'):
                        rec.message_post(body=fulfillment_res.get('errors'))
                    else:
                        rec.message_post(body="Shopify fulfillment created.")
                        rec.shopify_id = fulfillment_res.get('fulfillment').get('id')
                        rec.marketplace_instance_id = marketplace_instance_id

    def move_shopify_fulfillment_order(self, fulfillable_orders, shopify_location_id):
        self.ensure_one()
        for fulfillable_order in fulfillable_orders:
            marketplace_instance_id = self.sale_id.marketplace_instance_id
            if not getattr(marketplace_instance_id, "use_graphql", False):
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))
            mutation = """
            mutation SyncoriaFulfillmentMove($id: ID!, $newLocationId: ID!) {
              fulfillmentOrderMove(id: $id, newLocationId: $newLocationId) {
                movedFulfillmentOrder {
                  id
                  status
                  assignedLocation { location { id } }
                  lineItems(first: 250) {
                    nodes {
                      id
                      lineItem { id legacyResourceId }
                    }
                  }
                }
                userErrors { field message }
              }
            }
            """
            fulfillment_res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                headers={'X-Service-Key': marketplace_instance_id.token},
                url='/graphql.json',
                query=mutation,
                variables={
                    "id": fulfillable_order['id'],
                    "newLocationId": to_shopify_gid("Location", shopify_location_id),
                },
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
            )
            if fulfillment_res.get('errors'):
                self.message_post(body=fulfillment_res.get('errors'))
            else:
                moved = (((fulfillment_res.get("data") or {}).get("fulfillmentOrderMove") or {}).get("movedFulfillmentOrder") or {})
                if moved:
                    return {
                        "id": moved.get("id"),
                        "status": moved.get("status"),
                        "assigned_location_id": int((((moved.get("assignedLocation") or {}).get("location") or {}).get("id") or "0").split("/")[-1]),
                        "line_items": [{"id": li.get("id"), "line_item_id": int(((li.get("lineItem") or {}).get("legacyResourceId") or 0)) if (li.get("lineItem") or {}).get("legacyResourceId") else None} for li in (((moved.get("lineItems") or {}).get("nodes") or []))],
                    }
            continue


class InheritedStockLocation(models.Model):
    _inherit = 'stock.location'

    shopify_warehouse_ids = fields.Many2many("shopify.warehouse",string="Shopify Warehouse")


# class InheritedStockWarehouse(models.Model):
#     _inherit = 'stock.warehouse'
#
#     shopify_location_id = fields.Many2one("shopify.warehouse", string="Shopify Warehouse")
#     shopify_invent_id = fields.Char("Shopify Location ID", related="shopify_location_id.shopify_invent_id")
#
#     _sql_constraints = [
#         ('shopify_location_id', 'unique (shopify_location_id)', 'Only 1 odoo map 1 shopify location.'),
#     ]


class InheritedStockMove(models.Model):
    _inherit = 'stock.move'

    def write(self, vals):
        res = super(InheritedStockMove, self).write(vals)
        for rec in self:
            if rec.state == 'done' and rec.product_id:
                rec.product_id.shopify_need_sync = True
        return res

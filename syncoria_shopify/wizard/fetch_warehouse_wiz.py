# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import requests
import logging
import base64
import re
from odoo import api, models, fields, exceptions, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class WarehouseFetchWizard(models.TransientModel):
    _name = 'shopify.warehouse.fetch.wizard'
    _description = 'Shopify Warehouse Wizard'

    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
        required=True,
        domain="[('marketplace_instance_type', '=', 'shopify'), ('marketplace_state', '=', 'confirm')]",
    )

    def fetch_warehouse_to_odoo(self):
        marketplace_instance_id = self.instance_id
        if marketplace_instance_id:
            headers = {'X-Service-Key': marketplace_instance_id.token}
            if not getattr(marketplace_instance_id, "use_graphql", False):
                raise exceptions.UserError(
                    _("This fetch is GraphQL-only. Enable 'Use GraphQL' on the Shopify instance.")
                )
            if getattr(marketplace_instance_id, "use_graphql", False):
                query = """
                query SyncoriaLocations($first: Int!, $after: String) {
                  locations(first: $first, after: $after) {
                    edges {
                      node {
                        id
                        name
                        address {
                          address1
                          address2
                          city
                          zip
                          province
                          country
                          phone
                          countryCode
                          provinceCode
                        }
                        isActive
                      }
                    }
                    pageInfo { hasNextPage endCursor }
                  }
                }
                """
                all_locations = []
                after = None
                while True:
                    inventory_locations, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers=headers,
                        url='/graphql.json',
                        query=query,
                        variables={"first": 250, "after": after},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    if inventory_locations.get('errors'):
                        # Avoid UI showing "[object Object]" by coercing error dict to string.
                        raise exceptions.UserError(_(str(inventory_locations.get('errors'))))
                    conn = ((inventory_locations.get("data") or {}).get("locations") or {})
                    edges = conn.get("edges") or []
                    for edge in edges:
                        node = edge.get("node") or {}
                        addr = node.get("address") or {}
                        all_locations.append({
                            "id": (node.get("id") or "").split("/")[-1],
                            "name": node.get("name"),
                            "address1": addr.get("address1"),
                            "address2": addr.get("address2"),
                            "city": addr.get("city"),
                            "zip": addr.get("zip"),
                            "province": addr.get("province"),
                            "country": addr.get("country"),
                            "phone": addr.get("phone"),
                            "country_code": addr.get("countryCode"),
                            "province_code": addr.get("provinceCode"),
                            "legacy": False,
                            "active": node.get("isActive"),
                            "localized_country_name": addr.get("country"),
                            "localized_province_name": addr.get("province"),
                            "created_at": False,
                            "updated_at": False,
                            "country_name": addr.get("country"),
                        })
                    page_info = conn.get("pageInfo") or {}
                    if not page_info.get("hasNextPage"):
                        break
                    after = page_info.get("endCursor")
                inventory_locations = {"locations": all_locations}
            # REST path intentionally removed (GraphQL-only).

            _logger.info("inventory_locations====>>>{}".format(inventory_locations.get("locations", [])))


            shopify_warehouse = self.env['shopify.warehouse']
            for location in inventory_locations.get("locations", []):

                vals = {
                    "shopify_invent_id" : location.get("id"),
                    "shopify_loc_name" : location.get("name"),
                    "shopify_loc_add_one" : location.get("address1"),
                    "shopify_loc_add_two" : location.get("address2"),
                    "shopify_loc_city" : location.get("city"),
                    "shopify_loc_zip" : location.get("zip"),
                    "shopify_loc_province" : location.get("province"),
                    "shopify_loc_country" : location.get("country"),
                    "shopify_loc_phone" : location.get("phone"),
                    "shopify_loc_created_at" : location.get("created_at"),
                    "shopify_loc_updated_at" : location.get("updated_at"),
                    "shopify_loc_country_code" : location.get("country_code"),
                    "shopify_loc_country_name" : location.get("country_name"),
                    "shopify_loc_country_province_code" : location.get("province_code"),
                    "shopify_loc_legacy" : location.get("legacy"),
                    "shopify_loc_active" : location.get("active"),
                    "shopify_loc_localized_country_name" : location.get("localized_country_name"),
                    "shopify_loc_localized_province_name" : location.get("localized_province_name"),
                    "shopify_instance_id" : marketplace_instance_id.id,
                }

                exists_warehouse = shopify_warehouse.search([
                    ("shopify_invent_id", "=", location.get("id")),
                    ("shopify_instance_id", "=", marketplace_instance_id.id),
                ], limit=1)
                if not exists_warehouse:
                    exists_warehouse = shopify_warehouse.create(vals)
                else:
                    exists_warehouse.write(vals)

                # --- AUTO-MAPPING ---
                # Try to find a matching internal stock location by Shopify location name.
                sw_record = exists_warehouse
                loc_name = (location.get("name") or "").strip()
                odoo_location = self.env['stock.location'].search([
                    ('name', 'ilike', loc_name),
                    ('usage', '=', 'internal'),
                    ('active', '=', True),
                ], limit=1) if loc_name else self.env['stock.location']

                if not odoo_location:
                    # Fallback: map to the first active warehouse stock location.
                    default_wh = self.env['stock.warehouse'].search([('active', '=', True)], limit=1)
                    if default_wh:
                        odoo_location = default_wh.lot_stock_id
                        _logger.info(
                            "Fallback candidate for Shopify location '%s' (%s): %s",
                            loc_name, location.get("id"), odoo_location.display_name,
                        )

                if odoo_location and sw_record and sw_record not in odoo_location.shopify_warehouse_ids:
                    odoo_location.shopify_warehouse_ids = [(4, sw_record.id)]
                    _logger.info(
                        "Auto-mapped Shopify location '%s' (%s) -> Odoo location '%s'",
                        loc_name, location.get("id"), odoo_location.display_name,
                    )
                elif odoo_location and sw_record:
                    _logger.info(
                        "Shopify location '%s' (%s) already mapped to Odoo location '%s'",
                        loc_name, location.get("id"), odoo_location.display_name,
                    )
                else:
                    _logger.info(
                        "No auto-map found for Shopify location '%s' (%s) - manual mapping required.",
                        loc_name, location.get("id"),
                    )

        else:
            raise exceptions.UserError(
                _("Please select a confirmed Shopify marketplace instance.")
            )



# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################
import json
import logging
import datetime
import uuid
from markupsafe import Markup
from odoo import fields, models, exceptions, _
from odoo.http import request
import re
import pprint
import time

from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

def _to_gid(resource, numeric_id):
    """
    Shopify GraphQL IDs are global IDs (GIDs). Our DB typically stores legacy numeric IDs,
    but some flows may already store full GIDs. Avoid double-wrapping.
    """
    if not numeric_id:
        return False
    if isinstance(numeric_id, str) and numeric_id.startswith("gid://shopify/"):
        return numeric_id
    return "gid://shopify/%s/%s" % (resource, numeric_id)


class UpdateStockWizard(models.TransientModel):
    _inherit = 'update.stock.wizard'

    instance_id = fields.Many2one(
        string='Marketplace Instance',
        comodel_name='marketplace.instance',
        ondelete='restrict',
        required=False,
        domain="[('marketplace_state', '=', 'confirm')]"
    )
    source_location_ids = fields.Many2many('stock.location', string="Source Location")

    def _get_location_on_hand_qty(self, product, location):
        """Return the physical on-hand quantity for a product at a specific internal
        location. We send the gross on-hand (not available) to Shopify because Shopify
        manages its own committed/reserved quantities independently. Sending available
        (on_hand - reserved) would reduce Shopify's stock by Odoo's internal reservations,
        which are unrelated to Shopify's concept of committed stock."""
        quant_ids = self.env['stock.quant'].sudo().search([
            ('product_id', '=', product.id),
            ('location_id', '=', location.id),
            ('location_id.usage', '=', 'internal'),
        ])
        on_hand = sum(quant_ids.mapped('quantity'))
        return max(int(on_hand), 0)

    def shopify_update_stock_item(self):
        Connector = self.env['marketplace.connector']
        active_ids = self.env.context.get('active_ids')
        if self.fetch_type == 'to_odoo':
            if not self.instance_id:
                raise ValidationError(_("Please select a Shopify instance for stock import."))
            type_req = 'GET'
            products = self._shopify_get_product_list(active_ids)
            for item in products:
                try:
                    marketplace_instance_id = self.instance_id
                    mapping = self.env['shopify.product.mappings'].search([('product_id', '=', item.id), ('shopify_instance_id', '=', marketplace_instance_id.id)], limit=1)
                    if not mapping:
                        continue
                    if not getattr(marketplace_instance_id, "use_graphql", False):
                        raise ValidationError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")
                    levels = self._shopify_get_inventory_levels_graphql(
                        marketplace_instance_id=marketplace_instance_id,
                        inventory_item_id=mapping.shopify_inventory_id,
                    )
                    # Collect results for ALL locations then post ONE message per product.
                    location_results = []
                    for stocks_info in levels:
                        result = self.change_product_qty(stocks_info, item)
                        location_results.append(result)
                    self._post_import_summary(item, location_results)

                except Exception as e:
                    _logger.warning(e)
                    raise UserError(e)

            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }
        elif self.fetch_type == 'from_odoo':
            if not self.source_location_ids:
                raise ValidationError(_("Please select at least one source location for stock export."))
            products = self._shopify_get_product_list(active_ids)
            msg = ''
            for product in products:
                try:
                    for location in self.source_location_ids:
                        if not location.shopify_warehouse_ids:
                            _logger.warning(
                                'Export stock: location "%s" has no Shopify warehouse mapped — skipping.',
                                location.display_name,
                            )
                            product.message_post(
                                body='Export skipped for location "{}": no Shopify warehouse is mapped to this location. '
                                     'Go to Inventory → Configuration → Locations and add a Shopify Warehouse.'.format(
                                     location.display_name)
                            )
                            continue
                        for shopify_warehouse in location.shopify_warehouse_ids:
                            shopify_instance_id = shopify_warehouse.shopify_instance_id
                            prod_mapping = self.env['shopify.product.mappings'].search(
                                [('product_id', '=', product.id),
                                 ('shopify_instance_id', '=', shopify_instance_id.id)], limit=1)
                            if prod_mapping.shopify_id and prod_mapping.shopify_inventory_id:
                                try:
                                    qty_to_update = self._get_location_on_hand_qty(product, location)
                                    compare_qty = self._shopify_get_location_available_qty(
                                        shopify_instance_id,
                                        prod_mapping.shopify_inventory_id,
                                        shopify_warehouse.shopify_invent_id,
                                    )
                                    self._shopify_update_qty(
                                        warehouse=shopify_warehouse.shopify_invent_id,
                                        inventory_item_id=prod_mapping.shopify_inventory_id,
                                        quantity=qty_to_update,
                                        compare_quantity=compare_qty,
                                        marketplace_instance_id=shopify_instance_id,
                                    )
                                    log_body = Markup(
                                        '<b>Stock Export to Shopify</b><br/>'
                                        '<b>Location:</b> {loc}<br/>'
                                        '<b>Shopify Location:</b> {sloc} ({sid})<br/>'
                                        '<b>Store:</b> {store}<br/>'
                                        '<b>Shopify Before (available):</b> {before}<br/>'
                                        '<b>Odoo Sent (available):</b> {after}'
                                    ).format(
                                        loc=location.display_name,
                                        sloc=shopify_warehouse.shopify_loc_name,
                                        sid=shopify_warehouse.shopify_invent_id,
                                        store=shopify_instance_id.name,
                                        before=compare_qty,
                                        after=qty_to_update,
                                    )
                                    product.message_post(body=log_body)
                                    product.product_tmpl_id.message_post(body=log_body)
                                except Exception as e:
                                    _logger.warning("Error in Request: %s" % e.args)
                                    err_body = Markup(
                                        '<b>Stock Export to Shopify Failed</b><br/>'
                                        '<b>Location:</b> {loc}<br/>'
                                        '<b>Shopify Location:</b> {sloc}<br/>'
                                        '<b>Error:</b> {err}'
                                    ).format(
                                        loc=location.display_name,
                                        sloc=shopify_warehouse.shopify_loc_name,
                                        err=str(e),
                                    )
                                    product.message_post(body=err_body)
                                    product.product_tmpl_id.message_post(body=err_body)
                                    continue
                except Exception as e:
                    _logger.warning("Error in Request: %s" % (e.args))
                    raise ValidationError(e)
            return {
                'type': 'ir.actions.client',
                'tag': 'reload'
            }

    def shopify_update_price_item(self):
        Connector = self.env['marketplace.connector']
        active_ids = self.env.context.get('active_ids')
        products = self._shopify_get_product_list(active_ids)
        if not self.instance_id:
            raise ValidationError(_("Please select a Shopify instance."))
        if not products:
            raise ValidationError(_("Please select at least one product/product template, then run Update Price again."))
        final_errors = []
        success_count = 0
        for product in products:
            time.sleep(1)
            marketplace_instance_id = self.instance_id
            if not marketplace_instance_id.set_price:
                raise ValidationError('This Shopify Instance is not allowed to update price. Please go to the configuration and turn on this option')
            headers = {
                'X-Service-Key': marketplace_instance_id.token,
            }
            try:
                if marketplace_instance_id.set_price:
                    mapping_product_id = self.env['shopify.product.mappings'].search(
                        [('product_id', '=', product.id),
                         ('shopify_instance_id', '=', marketplace_instance_id.id)], limit=1)
                    # Resolve price robustly:
                    # 1) Try configured Shopify pricelist price.
                    # 2) Fall back to product/template sale price if pricelist returns empty.
                    product_price = None
                    if marketplace_instance_id.compute_pricelist_price:
                        try:
                            product_price = product.get_shopify_price(marketplace_instance_id)
                        except Exception as e:
                            _logger.info(
                                "Pricelist price resolution failed for %s (%s): %s",
                                product.display_name, product.id, e
                            )
                    if product_price in (None, False, ""):
                        product_price = product.lst_price or product.list_price or product.product_tmpl_id.list_price
                    if product_price in (None, False, ""):
                        final_errors.append(f'{product.name} (price not found)')
                        continue
                    price = product_price
                    if getattr(marketplace_instance_id, "use_graphql", False):
                        if not mapping_product_id or not mapping_product_id.shopify_parent_id or not mapping_product_id.shopify_id:
                            final_errors.append(f'{product.name} (missing Shopify mapping)')
                            continue
                        mutation = """
                            mutation SyncoriaVariantPriceUpdate($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
                              productVariantsBulkUpdate(productId: $productId, variants: $variants) {
                                product { id }
                                productVariants { id }
                                userErrors { field message }
                              }
                            }
                            """
                        variables = {
                            "productId": _to_gid("Product", mapping_product_id.shopify_parent_id),
                            "variants": [{
                                "id": _to_gid("ProductVariant", mapping_product_id.shopify_id),
                                "price": str(price),
                                "compareAtPrice": str(product.product_tmpl_id.shopify_compare_price) if product.product_tmpl_id.shopify_compare_price else None,
                            }],
                        }
                        # Remove null compareAtPrice to avoid userErrors.
                        variables["variants"][0] = {k: v for k, v in variables["variants"][0].items() if v is not None and v != ""}
                        stock_item, next_link = Connector.shopify_graphql_call(
                            headers=headers,
                            url='/graphql.json',
                            query=mutation,
                            variables=variables,
                            type='POST',
                            marketplace_instance_id=marketplace_instance_id,
                        )
                        payload = (stock_item.get("data") or {}).get("productVariantsBulkUpdate") or {}
                        user_errors = payload.get("userErrors") or []
                        if user_errors:
                            stock_item["errors"] = user_errors
                    else:
                        raise ValidationError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")
                    if stock_item.get('errors'):
                        errors = stock_item.get('errors', {})
                        _logger.warning(_("Request Error: %s" % errors))
                        product.message_post(body='Request Error: %s' % errors)
                        product.product_tmpl_id.message_post(
                            body='%s Request Error: %s' % (product.name, errors))
                        final_errors.append(f'{product.name} (Shopify error: {errors})')
                        continue
                    product.message_post(
                        body='Product {} ({}) updated price {} on store {}.\n'.format(
                            product.name, product.default_code, price, marketplace_instance_id.name))
                    product.product_tmpl_id.message_post(
                        body='Product {} ({}) updated price {} on store {}.\n'.format(
                            product.name, product.default_code, price, marketplace_instance_id.name))
                    product.action_update_shopify_cost_product(marketplace_instance_id)
                    success_count += 1
            except Exception as e:
                _logger.warning("Error in Request: %s" % e.args)
                final_errors.append(f'{product.name} ({e})')
                continue

        if success_count == 0 and not final_errors:
            raise ValidationError(_("No products were processed for Shopify price update."))
        if final_errors:
            error_message = "Failed to update price for the following products:\n"
            error_message += "\n".join(final_errors)
            raise ValidationError(error_message)

    def change_product_qty(self, stock_info, product_info):
        """Apply inventory update for one Shopify location.
        Returns a result dict for the caller to use when building the summary log."""
        shopify_location_id = stock_info.get("location_id")
        location_domain = [('shopify_warehouse_ids.shopify_invent_id', '=', shopify_location_id)]
        if self.instance_id:
            location_domain.append(('shopify_warehouse_ids.shopify_instance_id', '=', self.instance_id.id))
        location = self.env['stock.location'].search(location_domain, limit=1)
        if location:
            existing_quants = self.env['stock.quant'].sudo().search([
                ('product_id', '=', product_info.id),
                ('location_id', '=', location.id),
            ])
            qty_before = sum(existing_quants.mapped('quantity'))
            reserved_before = sum(existing_quants.mapped('reserved_quantity'))

            on_hand_qty = stock_info.get('on_hand', stock_info.get('available', 0))
            shopify_available = stock_info.get('available', 0)

            self.env['stock.quant'].with_context(inventory_mode=True).create({
                'product_id': product_info.id,
                'location_id': location.id,
                'inventory_quantity': on_hand_qty,
            }).action_apply_inventory()

            _logger.info(
                'Product %s: on-hand %s → %s at location %s (Shopify location %s)',
                product_info.display_name, int(qty_before), on_hand_qty,
                location.display_name, shopify_location_id,
            )
            return {
                'ok': True,
                'location_name': location.display_name,
                'shopify_location_id': shopify_location_id,
                'shopify_on_hand': on_hand_qty,
                'shopify_available': shopify_available,
                'odoo_before_on_hand': int(qty_before),
                'odoo_before_reserved': int(reserved_before),
                'odoo_after_on_hand': on_hand_qty,
                'odoo_after_reserved': int(reserved_before),
            }
        else:
            _logger.warning('Cannot find location that is mapped to shopify location id: %s', shopify_location_id)
            return {
                'ok': False,
                'shopify_location_id': shopify_location_id,
            }

    def _post_import_summary(self, product_info, location_results):
        """Post a single consolidated chatter message for all location results."""
        if not location_results:
            return

        rows = []
        for r in location_results:
            if r.get('ok'):
                before_avail = max(r['odoo_before_on_hand'] - r['odoo_before_reserved'], 0)
                after_avail = max(r['odoo_after_on_hand'] - r['odoo_after_reserved'], 0)
                rows.append(
                    '<tr style="background:#f0fdf4">'
                    '<td style="padding:4px 8px">✅ {loc}</td>'
                    '<td style="padding:4px 8px;text-align:center">{s_oh}</td>'
                    '<td style="padding:4px 8px;text-align:center">{s_av}</td>'
                    '<td style="padding:4px 8px;text-align:center">'
                    '{b_oh} / {b_res} / {b_av}</td>'
                    '<td style="padding:4px 8px;text-align:center">'
                    '<b>{a_oh}</b> / {a_res} / <b>{a_av}</b></td>'
                    '</tr>'.format(
                        loc=r['location_name'],
                        s_oh=r['shopify_on_hand'], s_av=r['shopify_available'],
                        b_oh=r['odoo_before_on_hand'], b_res=r['odoo_before_reserved'], b_av=before_avail,
                        a_oh=r['odoo_after_on_hand'], a_res=r['odoo_after_reserved'], a_av=after_avail,
                    )
                )
            else:
                rows.append(
                    '<tr style="background:#fef2f2">'
                    '<td colspan="5" style="padding:4px 8px">'
                    'Shopify location <b>{sid}</b> is not mapped to any Odoo location. '
                    'Go to <b>Inventory → Configuration → Locations</b> and add this '
                    'Shopify location under the <b>Shopify Warehouse</b> field.'
                    '</td>'
                    '</tr>'.format(sid=r['shopify_location_id'])
                )

        body = Markup(
            '<b>Stock Import from Shopify</b>'
            '<table style="width:100%;border-collapse:collapse;margin-top:6px;font-size:13px">'
            '<thead><tr style="background:#e5e7eb">'
            '<th style="padding:4px 8px;text-align:left">Odoo Location</th>'
            '<th style="padding:4px 8px">Shopify On Hand</th>'
            '<th style="padding:4px 8px">Shopify Available</th>'
            '<th style="padding:4px 8px">Before (OH / Res / Avail)</th>'
            '<th style="padding:4px 8px">After (OH / Res / Avail)</th>'
            '</tr></thead>'
            '<tbody>{rows}</tbody>'
            '</table>'
        ).format(rows=Markup(''.join(rows)))

        product_info.message_post(body=body)
        product_info.product_tmpl_id.message_post(body=body)

    def _shopify_get_inventory_levels_graphql(self, marketplace_instance_id, inventory_item_id):
        query = """
        query SyncoriaInventoryLevels($id: ID!) {
          inventoryItem(id: $id) {
            inventoryLevels(first: 250) {
              nodes {
                location { id }
                quantities(names: ["available", "on_hand"]) {
                  name
                  quantity
                }
              }
            }
          }
        }
        """
        res, _next = self.env['marketplace.connector'].shopify_graphql_call(
            headers={'X-Service-Key': marketplace_instance_id.token},
            url='/graphql.json',
            query=query,
            variables={"id": _to_gid("InventoryItem", inventory_item_id)},
            type='POST',
            marketplace_instance_id=marketplace_instance_id,
        )
        if res.get('errors'):
            raise UserError(res.get('errors'))
        nodes = (((res.get("data") or {}).get("inventoryItem") or {}).get("inventoryLevels") or {}).get("nodes") or []
        levels = []
        for node in nodes:
            loc_id = ((node.get("location") or {}).get("id") or "").split("/")[-1]
            available = 0
            on_hand = 0
            for q in node.get("quantities") or []:
                if q.get("name") == "available":
                    available = int(q.get("quantity") or 0)
                elif q.get("name") == "on_hand":
                    on_hand = int(q.get("quantity") or 0)
            levels.append({
                "location_id": loc_id,
                "available": available,
                "on_hand": on_hand,
            })
        return levels

    def _shopify_get_location_available_qty(self, marketplace_instance_id, inventory_item_id, location_id):
        """Return the current 'available' quantity from Shopify for one item/location.
        Used as changeFromQuantity in inventorySetQuantities to satisfy the API requirement."""
        query = """
        query SyncoriaCurrentInventory($itemId: ID!, $locationId: ID!) {
          inventoryItem(id: $itemId) {
            inventoryLevel(locationId: $locationId) {
              quantities(names: ["available"]) {
                name
                quantity
              }
            }
          }
        }
        """
        res, _next = self.env['marketplace.connector'].shopify_graphql_call(
            headers={'X-Service-Key': marketplace_instance_id.token},
            url='/graphql.json',
            query=query,
            variables={
                "itemId": _to_gid("InventoryItem", inventory_item_id),
                "locationId": _to_gid("Location", location_id),
            },
            type='POST',
            marketplace_instance_id=marketplace_instance_id,
        )
        level = ((res.get("data") or {}).get("inventoryItem") or {}).get("inventoryLevel") or {}
        for q in (level.get("quantities") or []):
            if q.get("name") == "available":
                return int(q.get("quantity") or 0)
        return 0

    def _shopify_update_qty(self, **kwargs):
        """Set inventory to an absolute quantity by computing the delta against the
        current Shopify available (compare_quantity) and calling inventoryAdjustQuantities.
        A per-call UUID is embedded in the @idempotent directive as required by Shopify."""
        Connector = self.env['marketplace.connector']
        _logger.info(kwargs)
        if not getattr(kwargs["marketplace_instance_id"], "use_graphql", False):
            raise ValidationError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")
        desired = int(kwargs['quantity'])
        current = int(kwargs.get('compare_quantity', 0))
        delta = desired - current
        _logger.info(
            "Shopify inventory adjust: current=%s desired=%s delta=%s item=%s location=%s",
            current, desired, delta, kwargs['inventory_item_id'], kwargs['warehouse'],
        )
        idempotent_key = str(uuid.uuid4())
        mutation = (
            'mutation SyncoriaInventoryAdjust($input: InventoryAdjustQuantitiesInput!) {'
            '  inventoryAdjustQuantities(input: $input) @idempotent(key: "%s") {'
            '    inventoryAdjustmentGroup { createdAt reason }'
            '    userErrors { field message }'
            '  }'
            '}'
        ) % idempotent_key
        variables = {
            "input": {
                "name": "available",
                "reason": "correction",
                "changes": [
                    {
                        "inventoryItemId": _to_gid("InventoryItem", kwargs['inventory_item_id']),
                        "locationId": _to_gid("Location", kwargs['warehouse']),
                        "delta": delta,
                        "changeFromQuantity": current,
                    }
                ],
            }
        }
        stock_item, _next = Connector.shopify_graphql_call(
            headers={'X-Service-Key': kwargs["marketplace_instance_id"].token},
            url='/graphql.json',
            query=mutation,
            variables=variables,
            type='POST',
            marketplace_instance_id=kwargs["marketplace_instance_id"],
        )
        _logger.info("stock_item: %s", stock_item)
        payload = ((stock_item.get("data") or {}).get("inventoryAdjustQuantities") or {})
        user_errors = payload.get("userErrors") or []
        if user_errors:
            raise Exception(user_errors)
        if stock_item.get('errors'):
            raise Exception(stock_item.get('errors'))
        return

    def _shopify_adjust_qty(self, **kwargs):
        Connector = self.env['marketplace.connector']
        if not getattr(kwargs["marketplace_instance_id"], "use_graphql", False):
            raise ValidationError("GraphQL-only: enable 'Use GraphQL' on the Shopify instance.")
        idempotent_key = str(uuid.uuid4())
        mutation = (
            'mutation SyncoriaInventoryAdjust($input: InventoryAdjustQuantitiesInput!) {'
            '  inventoryAdjustQuantities(input: $input) @idempotent(key: "%s") {'
            '    inventoryAdjustmentGroup { createdAt reason }'
            '    userErrors { field message }'
            '  }'
            '}'
        ) % idempotent_key
        variables = {
            "input": {
                "name": "available",
                "reason": "correction",
                "changes": [
                    {
                        "inventoryItemId": _to_gid("InventoryItem", kwargs['inventory_item_id']),
                        "locationId": _to_gid("Location", kwargs['warehouse']),
                        "delta": int(kwargs['quantity']),
                    }
                ],
            }
        }
        stock_item, _next = Connector.shopify_graphql_call(
            headers={'X-Service-Key': kwargs["marketplace_instance_id"].token},
            url='/graphql.json',
            query=mutation,
            variables=variables,
            type='POST',
            marketplace_instance_id=kwargs["marketplace_instance_id"],
        )
        _logger.info("stock_item: %s", stock_item)
        if stock_item.get('errors'):
            raise Exception(stock_item.get('errors'))
        return

    def _shopify_get_product_list(self, active_ids):
        products = self.env['product.product']
        if self.env.context.get('active_model') == 'product.product':
            products = self.env['product.product'].search([
                ('id', 'in', active_ids),
            ])
        if self.env.context.get('active_model') == 'product.template':
            products = self.env['product.product'].search([
                ('product_tmpl_id', 'in', active_ids),
            ])
        return products

    def ir_cron_need_sync_stock(self, location_id):
        # Backward/forward compatible cron signature:
        # - new: ir_cron_need_sync_stock(location_id=<stock.location id>)
        # - legacy XML in some databases used: ir_cron_need_sync_stock(warehouse_id=..., instance_id=...)
        if isinstance(location_id, dict):
            location_id = location_id.get("location_id") or location_id.get("warehouse_id")
        location = self.env['stock.location'].browse(location_id)
        if not location.exists():
            return
        products = self.env['product.product'].search([('shopify_need_sync', '=', True)])
        for product in products:
            for shopify_warehouse in location.shopify_warehouse_ids:
                shopify_instance_id = shopify_warehouse.shopify_instance_id
                prod_mapping = self.env['shopify.product.mappings'].search(
                    [('product_id', '=', product.id),
                     ('shopify_instance_id', '=', shopify_instance_id.id)], limit=1)
                if prod_mapping.shopify_id and prod_mapping.shopify_inventory_id:
                    try:
                        qty_to_update = self._get_location_on_hand_qty(product, location)
                        compare_qty = self._shopify_get_location_available_qty(
                            shopify_instance_id,
                            prod_mapping.shopify_inventory_id,
                            shopify_warehouse.shopify_invent_id,
                        )
                        self._shopify_update_qty(
                            warehouse=shopify_warehouse.shopify_invent_id,
                            inventory_item_id=prod_mapping.shopify_inventory_id,
                            quantity=qty_to_update,
                            compare_quantity=compare_qty,
                            marketplace_instance_id=shopify_instance_id,
                        )
                        log_body = Markup(
                            '<b>Stock Auto-Sync to Shopify</b><br/>'
                            '<b>Location:</b> {loc}<br/>'
                            '<b>Shopify Location:</b> {sloc} ({sid})<br/>'
                            '<b>Store:</b> {store}<br/>'
                            '<b>Shopify Before (available):</b> {before}<br/>'
                            '<b>Odoo Sent (available):</b> {after}'
                        ).format(
                            loc=location.display_name,
                            sloc=shopify_warehouse.shopify_loc_name,
                            sid=shopify_warehouse.shopify_invent_id,
                            store=shopify_instance_id.name,
                            before=compare_qty,
                            after=qty_to_update,
                        )
                        product.message_post(body=log_body)
                        product.product_tmpl_id.message_post(body=log_body)
                    except Exception as e:
                        _logger.warning("Error in Request: %s" % e.args)
                        err_body = Markup(
                            '<b>Stock Auto-Sync to Shopify Failed</b><br/>'
                            '<b>Location:</b> {loc}<br/>'
                            '<b>Shopify Location:</b> {sloc}<br/>'
                            '<b>Error:</b> {err}'
                        ).format(
                            loc=location.display_name,
                            sloc=shopify_warehouse.shopify_loc_name,
                            err=str(e),
                        )
                        product.message_post(body=err_body)
                        product.product_tmpl_id.message_post(body=err_body)
                        continue
            product.shopify_need_sync = False

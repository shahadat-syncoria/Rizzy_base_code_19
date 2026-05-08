# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import json
import logging
import datetime
from odoo import api, fields, models, exceptions, _
from ..shopify.utils import parse_gql_nodes

_logger = logging.getLogger(__name__)


def get_address_vals(env, address):
    """Build res.partner child-address values from Shopify address payload."""
    address = address or {}
    country = False
    state = False

    country_domain = []
    if address.get("country_code"):
        country_domain += [("code", "=", address.get("country_code"))]
    elif address.get("country"):
        country_domain += [("name", "=", address.get("country"))]
    if country_domain:
        country = env["res.country"].sudo().search(country_domain, limit=1)

    state_domain = [("country_id", "=", country.id)] if country else []
    if address.get("province_code"):
        state_domain += [("code", "=", address.get("province_code"))]
    elif address.get("province"):
        state_domain += [("name", "=", address.get("province"))]
    if state_domain:
        state = env["res.country.state"].sudo().search(state_domain, limit=1)

    vals = {
        "name": address.get("name") or (
            ((address.get("first_name") or address.get("firstName") or "") + " " +
             (address.get("last_name") or address.get("lastName") or "")).strip()
        ),
        "street": address.get("address1") or "",
        "street2": address.get("address2") or "",
        "city": address.get("city") or "",
        "zip": address.get("zip") or "",
        "phone": address.get("phone") or "",
        "company_name": address.get("company") or "",
        "country_id": country.id if country else None,
        "state_id": state.id if state else None,
        "shopify_add_id": address.get("id"),
    }
    # Optional custom fields: only set if present in this DB schema.
    partner_fields = env['res.partner']._fields
    if 'group_rfq' in partner_fields:
        vals['group_rfq'] = False
    if 'group_on' in partner_fields:
        vals['group_on'] = False
    return vals


class OrderFetchWizard(models.TransientModel):
    _inherit = 'order.fetch.wizard'

    @api.model
    def default_get(self, fields_list):
        """Full sync needs only the marketplace instance; optional filters narrow the run."""
        res = super().default_get(fields_list)
        if self.env.context.get('shopify_keep_fetch_wizard_defaults'):
            return res
        for fname in (
            'date_from',
            'date_to',
            'shopify_order_no',
            'feed_only',
            'shopify_customer_no',
        ):
            if fname in fields_list:
                res[fname] = False
        return res

    order_status = fields.Selection(selection_add=[
            ('any', 'All'),
            ('open', 'Opened'),
            ('closed', 'Closed'),
            ('cancelled', 'Cancelled')
        ], string="Order Status",default='any')
    shopify_order_no = fields.Char()
    feed_only = fields.Boolean(string='Fetch Feed Order only', default=False)

    def fetch_query(self, vals):
        """constructing the query, from the provided column names"""
        query_str = ""
        if not vals:
            return
        for col in vals:
            query_str += " " + str(col) + ","
        return query_str[:-1]

    def cron_shopify_fetch_orders(self, instance_id=None):
        """Cron entrypoint: fetch orders for one/all confirmed Shopify instances."""
        Instance = self.env['marketplace.instance']
        if instance_id:
            instances = Instance.browse(instance_id).exists()
        else:
            instances = Instance.search([
                ('marketplace_instance_type', '=', 'shopify'),
                ('marketplace_state', '=', 'confirm'),
            ])
        for rec in instances:
            try:
                wizard_id = self.create({'instance_id': rec.id})
                wizard_id.fetch_orders()
            except Exception as e:
                self.env['marketplace.logging'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('marketplace.logging'),
                    'create_uid': self.env.user.id,
                    'marketplace_instance_id': rec.id,
                    'level': 'warning',
                    'type': 'client',
                    'summary': 'Shopify cron order fetch failed',
                    'error': str(e).replace('<br>', '').replace('</br>', '\n'),
                })

    def shopify_fetch_orders(self, kwargs=None):
        """Function to Fetch Orders From Shopify

        Args:
            kwargs (dict, marketplace_instance_id): Dictionary. Marketplace Instance ID.

        Returns:
            action: Action
        """

        marketplace_instance_id = kwargs.get("marketplace_instance_id") or self.instance_id
        use_graphql = getattr(marketplace_instance_id, "use_graphql", False)
        if not use_graphql:
            raise exceptions.UserError(
                _("This fetch is GraphQL-only. Enable 'Use GraphQL' on the Shopify instance.")
            )
        order_list = {"orders": self._shopify_fetch_orders_graphql(marketplace_instance_id)}
        _logger.info("Order #(GraphQL)==>>>>{}".format(len(order_list.get('orders'))))
        try:
            log_msg = ''
            error_msg = ''
            sp_orders = order_list['orders']

            feed_order_list = []
            for i in sp_orders:
                feed_order_id, feed_log_msg, feed_error_msg = self.create_feed_orders(
                    i, marketplace_instance_id=marketplace_instance_id)
                log_msg += feed_log_msg
                error_msg += feed_error_msg
                if not feed_order_id:
                    continue
                feed_order_list += feed_order_id.ids
                if not self.feed_only:
                    process_log_msg, process_error_msg = feed_order_id.process_feed_order()
                    log_msg += process_log_msg
                    error_msg += process_error_msg

            try:
                if feed_order_list and marketplace_instance_id:
                    log_id = self.env['marketplace.logging'].sudo().create({
                        'name': self.env['ir.sequence'].next_by_code('marketplace.logging'),
                        'create_uid': self.env.user.id,
                        'marketplace_instance_id': marketplace_instance_id.id,
                        'level': 'info',
                        'summary': log_msg.replace('<br>', '').replace('</br>', '\n'),
                        'error': error_msg.replace('<br>', '').replace('</br>', '\n'),
                    })
                    log_id.env.cr.commit()
            except Exception as e:
                _logger.exception("Exception-{}".format(e.args))
        except Exception as e:
            _logger.warning("Exception occured %s", e)
            raise exceptions.UserError(_("Error Occured:\n %s") % e)
        return

    def _shopify_fetch_orders_graphql(self, marketplace_instance_id):
        headers = {'X-Service-Key': marketplace_instance_id.token}

        # Shopify may restrict full history access depending on app permissions.
        # Keep fetch usable: when no filters are provided, default to a recent safe window.
        date_from = self.date_from
        date_to = self.date_to
        if not date_from and not date_to:
            date_from = fields.Date.to_date(fields.Date.context_today(self)) - datetime.timedelta(days=60)
            _logger.warning(
                "No date filter provided for order fetch; defaulting to last 60 days from %s.",
                date_from,
            )

        def _money(v):
            if v is None:
                return None
            return str(v)

        def _addr(address):
            if not address:
                return {}
            return {
                "address1": address.get("address1"),
                "address2": address.get("address2"),
                "city": address.get("city"),
                "company": address.get("company"),
                "first_name": address.get("firstName"),
                "last_name": address.get("lastName"),
                "phone": address.get("phone"),
                "province": address.get("province"),
                "country": address.get("country"),
                "zip": address.get("zip"),
                "name": address.get("name"),
                "province_code": address.get("provinceCode"),
                "country_code": address.get("countryCodeV2"),
                "country_name": address.get("country"),
            }

        def _money_bag(mb):
            mb = mb or {}
            return {
                "shop_money": mb.get("shopMoney") or {},
                "presentment_money": mb.get("presentmentMoney") or {},
            }

        def _gql_items(container, path=None):
            """
            Normalize GraphQL collections that can be shaped as:
            - list
            - {nodes: [...]}
            - {edges: [{node: ...}]}
            - single dict
            """
            node = container
            if path:
                for key in path:
                    if not isinstance(node, dict):
                        return []
                    node = node.get(key)
            if not node:
                return []
            if isinstance(node, list):
                return node
            if isinstance(node, dict):
                if isinstance(node.get("nodes"), list):
                    return node.get("nodes") or []
                if isinstance(node.get("edges"), list):
                    return [e.get("node") for e in (node.get("edges") or []) if isinstance(e, dict) and e.get("node")]
                return [node]
            return []

        query = """
        query SyncoriaOrders($first: Int!, $after: String, $query: String) {
          orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT) {
            edges {
              node {
                id
                name
                confirmed
                createdAt
                updatedAt
                totalPriceSet { shopMoney { amount currencyCode } }
                currentTotalPriceSet {
                  shopMoney { amount currencyCode }
                  presentmentMoney { amount currencyCode }
                }
                displayFinancialStatus
                displayFulfillmentStatus
                currencyCode
                cancelReason
                cancelledAt
                tags
                app { id }
                discountCodes
                customer {
                  id
                  firstName
                  lastName
                  email
                  phone
                  defaultAddress {
                    address1
                    address2
                    city
                    company
                    firstName
                    lastName
                    phone
                    province
                    country
                    zip
                    name
                    provinceCode
                    countryCodeV2
                  }
                }
                shippingAddress {
                  address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2
                }
                billingAddress {
                  address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2
                }
                lineItems(first: 250) {
                  edges {
                    node {
                      id
                      title
                      quantity
                      variant { id sku }
                      product { id }
                      discountedUnitPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
                      taxLines { title rate priceSet { shopMoney { amount } } }
                    }
                  }
                }
                shippingLines(first: 10) {
                  nodes {
                    title
                    code
                    discountedPriceSet { shopMoney { amount currencyCode } presentmentMoney { amount currencyCode } }
                    taxLines { title rate priceSet { shopMoney { amount } } }
                  }
                }
                transactions(first: 50) {
                  id
                  kind
                  status
                  gateway
                  manualPaymentGateway
                  processedAt
                  amountSet {
                    shopMoney { amount currencyCode }
                    presentmentMoney { amount currencyCode }
                  }
                  receiptJson
                }
                refunds(first: 20) {
                  id
                  note
                  createdAt
                  refundLineItems(first: 250) {
                    edges {
                      node {
                        quantity
                        lineItem {
                          id
                          quantity
                          title
                          variant { id sku }
                          product { id }
                        }
                      }
                    }
                  }
                  transactions(first: 50) {
                    edges {
                      node {
                        id
                        kind
                        status
                        gateway
                        manualPaymentGateway
                        processedAt
                        amountSet {
                          shopMoney { amount currencyCode }
                          presentmentMoney { amount currencyCode }
                        }
                        receiptJson
                      }
                    }
                  }
                }
                fulfillments(first: 20) {
                  id
                  status
                  createdAt
                  updatedAt
                  trackingInfo {
                    number
                    url
                    company
                  }
                }
              }
            }
            pageInfo { hasNextPage endCursor }
          }
        }
        """

        query_parts = []
        # Match REST `status=any` behavior (include open/closed/cancelled).
        # Without a status filter Shopify search commonly returns only open orders.
        if self.order_status:
            if self.order_status == "any":
                query_parts.append("status:any")
            else:
                query_parts.append("status:%s" % self.order_status)
        order_name_filter = (self.shopify_order_no or "").strip()
        if order_name_filter:
            # Support users entering either '#1001' or '1001'.
            normalized_order_name = order_name_filter if order_name_filter.startswith("#") else "#%s" % order_name_filter
            query_parts.append("name:%s" % normalized_order_name)
        else:
            # Match wizard "From/To" to order placement date (REST used created_at_*), not last updated.
            # When explicit order number is provided, avoid date filters so exact-order fetch still works.
            if date_from:
                query_parts.append("created_at:>=%s" % date_from.strftime("%Y-%m-%d"))
            if date_to:
                query_parts.append("created_at:<=%s" % date_to.strftime("%Y-%m-%d"))
        query_str = " ".join(query_parts).strip() or None
        all_orders = []
        after = None
        while True:
            res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                headers=headers,
                url='/graphql.json',
                query=query,
                variables={
                    "first": 25,
                    "after": after,
                    "query": query_str,
                },
                type='POST',
                marketplace_instance_id=marketplace_instance_id,
            )
            if res.get('errors'):
                gql_errors = res.get('errors') or []
                access_denied = any(
                    (err.get('extensions') or {}).get('code') == 'ACCESS_DENIED'
                    for err in gql_errors if isinstance(err, dict)
                )
                orders_denied = any(
                    'orders' in (err.get('path') or [])
                    for err in gql_errors if isinstance(err, dict)
                )
                if access_denied and orders_denied:
                    raise exceptions.UserError(_(
                        "Shopify denied access to Orders for this app (Protected Customer Data restriction). "
                        "This app must be approved/configured to read orders. "
                        "Until then, order import via API is not possible for this store."
                    ))
                raise exceptions.UserError(_("Error Occured %s") % res.get('errors'))
            conn = ((res.get("data") or {}).get("orders") or {})
            for n in parse_gql_nodes(conn):
                def _gid_id(v):
                    if not v:
                        return None
                    return int(str(v).split("/")[-1])
                customer = n.get("customer") or {}
                order = {
                    "id": _gid_id(n.get("id")) or 0,
                    "name": n.get("name"),
                    "confirmed": n.get("confirmed"),
                    "contact_email": customer.get("email"),
                    "created_at": n.get("createdAt"),
                    "updated_at": n.get("updatedAt"),
                    "total_price": _money((((n.get("totalPriceSet") or {}).get("shopMoney")) or {}).get("amount")),
                    "current_total_price_set": {
                        "shop_money": (n.get("currentTotalPriceSet") or {}).get("shopMoney") or {},
                        "presentment_money": (n.get("currentTotalPriceSet") or {}).get("presentmentMoney") or {},
                    },
                    "currency": n.get("currencyCode"),
                    "gateway": None,
                    "order_number": _gid_id(n.get("id")),
                    "financial_status": (n.get("displayFinancialStatus") or "").lower(),
                    "fulfillment_status": (n.get("displayFulfillmentStatus") or "").lower(),
                    "browser_ip": None,
                    "buyer_accepts_marketing": None,
                    "cancel_reason": n.get("cancelReason"),
                    "cancelled_at": n.get("cancelledAt"),
                    "cart_token": None,
                    "checkout_token": None,
                    "tags": ",".join(n.get("tags") or []),
                    "app_id": int((n.get("app") or {}).get("id", "0").split("/")[-1]) if (n.get("app") or {}).get("id") else None,
                    "discount_codes": [{"code": c, "amount": "0.0", "type": "fixed_amount"} for c in (n.get("discountCodes") or [])],
                    "customer": {
                        "id": _gid_id(customer.get("id")),
                        "first_name": customer.get("firstName"),
                        "last_name": customer.get("lastName"),
                        "email": customer.get("email"),
                        "phone": customer.get("phone"),
                        "default_address": _addr(customer.get("defaultAddress")),
                        "addresses": [_addr(customer.get("defaultAddress"))] if customer.get("defaultAddress") else [],
                    },
                    "shipping_address": _addr(n.get("shippingAddress")),
                    "billing_address": _addr(n.get("billingAddress")),
                    "line_items": [],
                    "shipping_lines": [],
                    "transactions": [],
                    "refunds": [],
                    "fulfillments": [],
                }
                for li in parse_gql_nodes(n, ("lineItems",)):
                    order["line_items"].append({
                        "id": _gid_id(li.get("id")),
                        "name": li.get("title"),
                        "title": li.get("title"),
                        "sku": ((li.get("variant") or {}).get("sku")),
                        "quantity": li.get("quantity"),
                        "variant_id": _gid_id((li.get("variant") or {}).get("id")),
                        "product_id": _gid_id((li.get("product") or {}).get("id")),
                        "price": _money(((li.get("discountedUnitPriceSet") or {}).get("shopMoney") or {}).get("amount")),
                        "price_set": {
                            "shop_money": (li.get("discountedUnitPriceSet") or {}).get("shopMoney") or {},
                            "presentment_money": (li.get("discountedUnitPriceSet") or {}).get("presentmentMoney") or {},
                        },
                        "discount_allocations": [],
                        "tax_lines": [{"title": tl.get("title"), "rate": tl.get("rate"), "price": _money(((tl.get("priceSet") or {}).get("shopMoney") or {}).get("amount"))} for tl in (li.get("taxLines") or [])],
                    })
                for sl in ((n.get("shippingLines") or {}).get("nodes") or []):
                    order["shipping_lines"].append({
                        "title": sl.get("title"),
                        "code": sl.get("code"),
                        "price": _money(((sl.get("discountedPriceSet") or {}).get("shopMoney") or {}).get("amount")),
                        "discounted_price": _money(((sl.get("discountedPriceSet") or {}).get("shopMoney") or {}).get("amount")),
                        "price_set": {"shop_money": (sl.get("discountedPriceSet") or {}).get("shopMoney") or {}, "presentment_money": (sl.get("discountedPriceSet") or {}).get("presentmentMoney") or {}},
                        "tax_lines": [{"title": tl.get("title"), "rate": tl.get("rate"), "price": _money(((tl.get("priceSet") or {}).get("shopMoney") or {}).get("amount"))} for tl in (sl.get("taxLines") or [])],
                    })
                for tx in _gql_items(n, ("transactions",)):
                    order["transactions"].append({
                        "id": _gid_id(tx.get("id")),
                        "kind": tx.get("kind").lower() if tx.get("kind") else None,
                        "status": tx.get("status").lower() if tx.get("status") else None,
                        "gateway": tx.get("gateway"),
                        "manual_payment_gateway": tx.get("manualPaymentGateway"),
                        "processed_at": tx.get("processedAt"),
                        "amount": _money((((tx.get("amountSet") or {}).get("shopMoney")) or {}).get("amount")),
                        "amount_set": _money_bag(tx.get("amountSet")),
                        "receipt": tx.get("receiptJson"),
                    })
                for refund in _gql_items(n, ("refunds",)):
                    refund_item = {
                        "id": _gid_id(refund.get("id")),
                        "note": refund.get("note"),
                        "created_at": refund.get("createdAt"),
                        "refund_line_items": [],
                        "transactions": [],
                    }
                    for rli in _gql_items(refund, ("refundLineItems",)):
                        line_item = rli.get("lineItem") or {}
                        refund_item["refund_line_items"].append({
                            "quantity": rli.get("quantity"),
                            "line_item": {
                                "id": _gid_id(line_item.get("id")),
                                "quantity": line_item.get("quantity"),
                                "title": line_item.get("title"),
                                "variant_id": _gid_id((line_item.get("variant") or {}).get("id")),
                                "product_id": _gid_id((line_item.get("product") or {}).get("id")),
                                "sku": ((line_item.get("variant") or {}).get("sku")),
                            }
                        })
                    for rtx in _gql_items(refund, ("transactions",)):
                        refund_item["transactions"].append({
                            "id": _gid_id(rtx.get("id")),
                            "kind": rtx.get("kind").lower() if rtx.get("kind") else None,
                            "status": rtx.get("status").lower() if rtx.get("status") else None,
                            "gateway": rtx.get("gateway"),
                            "manual_payment_gateway": rtx.get("manualPaymentGateway"),
                            "processed_at": rtx.get("processedAt"),
                            "amount": _money((((rtx.get("amountSet") or {}).get("shopMoney")) or {}).get("amount")),
                            "amount_set": _money_bag(rtx.get("amountSet")),
                            "receipt": rtx.get("receiptJson"),
                        })
                    order["refunds"].append(refund_item)
                for fulfillment in _gql_items(n, ("fulfillments",)):
                    order["fulfillments"].append({
                        "id": _gid_id(fulfillment.get("id")),
                        "status": fulfillment.get("status").lower() if fulfillment.get("status") else None,
                        "created_at": fulfillment.get("createdAt"),
                        "updated_at": fulfillment.get("updatedAt"),
                        "tracking_info": [
                            {
                                "number": t.get("number"),
                                "url": t.get("url"),
                                "company": t.get("company"),
                            }
                            for t in (fulfillment.get("trackingInfo") or [])
                        ],
                    })
                all_orders.append(order)
            page_info = conn.get("pageInfo") or {}
            if not page_info.get("hasNextPage"):
                break
            after = page_info.get("endCursor")

        _logger.info(
            "Shopify GraphQL fetched %s orders for instance %s. Printing full order payloads below.",
            len(all_orders),
            marketplace_instance_id.id,
        )
        for idx, order in enumerate(all_orders, start=1):
            _logger.info(
                "Shopify Order [%s/%s] %s",
                idx,
                len(all_orders),
                json.dumps(order, ensure_ascii=False, default=str),
            )
        return all_orders

    def create_feed_orders(self, order_data, marketplace_instance_id=None):
        log_msg = ''
        error_msg = ''
        feed_order_id = False
        try:
            marketplace_instance_id = marketplace_instance_id or self.instance_id
            if not marketplace_instance_id:
                raise exceptions.UserError(_("Missing marketplace instance for order feed."))
            customer_first_name = order_data.get('customer', {}).get('first_name', '') if order_data.get('customer',
                                                                                                         {}).get(
                'first_name', '') else ''
            customer_last_name = order_data.get('customer', {}).get('last_name', '') if order_data.get('customer',
                                                                                                       {}).get(
                'last_name', '') else ''
            customer_name = customer_first_name + ' ' + customer_last_name
            domain = [('shopify_id', '=', order_data['id'])]
            domain += [('instance_id', '=', marketplace_instance_id.id)]
            feed_order_id = self.env['shopify.feed.orders'].sudo().search(domain, limit=1)
            if not feed_order_id:
                feed_order_id = self.env['shopify.feed.orders'].sudo().create({
                    'name': self.env['ir.sequence'].sudo().next_by_code('shopify.feed.orders'),
                    'instance_id': marketplace_instance_id.id,
                    'shopify_id': order_data['id'],
                    'order_data': json.dumps(order_data),
                    'state': 'draft',
                    'shopify_webhook_call': False,
                    'shopify_app_id': order_data.get('app_id'),
                    'shopify_confirmed': order_data.get('confirmed'),
                    'shopify_contact_email': order_data.get('contact_email'),
                    'shopify_currency': order_data.get('currency'),
                    'shopify_customer_name': customer_name,
                    'shopify_customer_id': order_data.get('customer', {}).get('id', ''),
                    'shopify_gateway': order_data.get('gateway'),
                    'shopify_order_number': order_data.get('order_number'),
                    'shopify_financial_status': order_data.get('financial_status'),
                    'shopify_fulfillment_status': order_data.get('fulfillment_status'),
                    'shopify_line_items': len(order_data.get('line_items')),
                    'shopify_user_id': order_data.get('user_id'),
                })

                msg = _("Shopify Feed Order Created-{}".format(feed_order_id))
                _logger.info(msg)
                log_msg += "<br>" + msg + "</br>"
            else:
                feed_order_id.write({
                    'order_data': json.dumps(order_data),
                    'shopify_app_id': order_data.get('app_id'),
                    'shopify_confirmed': order_data.get('confirmed'),
                    'shopify_contact_email': order_data.get('contact_email'),
                    'shopify_currency': order_data.get('currency'),
                    'shopify_customer_name': customer_name,
                    'shopify_customer_id': order_data.get('customer', {}).get('id', ''),
                    'shopify_gateway': order_data.get('gateway'),
                    'shopify_order_number': order_data.get('order_number'),
                    'shopify_financial_status': order_data.get('financial_status'),
                    'shopify_fulfillment_status': order_data.get('fulfillment_status'),
                    'shopify_line_items': len(order_data.get('line_items')),
                    'shopify_user_id': order_data.get('user_id'),
                })

                msg = _("\nShopify Feed Order Updated-{}".format(feed_order_id))
                _logger.info(msg)
                log_msg += "<br>" + msg + "</br>"

            # feed_order_id._cr.commit()
        except Exception as e:
            error_msg += '<br> Shopify Order Feed Order Creation: {} Exception-{} </br>'.format(
                order_data.get('order_number'), e.args)
        return feed_order_id, log_msg, error_msg

    # def _get_inv_vals(self, order_id, sp_order):
    #     inv_vals = {}
    #     mkplc_id = self._get_instance_id()
    #     inv_vals.update({
    #         "ref": "",
    #         "move_type": "out_invoice",
    #         "narration": "",
    #         "currency_id": order_id.currency_id.id,
    #         "campaign_id": order_id.campaign_id.id,
    #         "medium_id": order_id.medium_id.id,
    #         "source_id": order_id.source_id.id,
    #         "user_id": order_id.user_id.id,
    #         "invoice_user_id": order_id.user_id.id,
    #         "team_id": order_id.team_id.id,
    #         "partner_id": order_id.partner_id.id,
    #         "partner_shipping_id": order_id.partner_shipping_id.id,
    #         "fiscal_position_id": order_id.fiscal_position_id.id,
    #         # "partner_bank_id": order_id.partner_bank_id.id,
    #         "journal_id": mkplc_id.marketplace_journal_id.id,
    #         "invoice_origin": order_id.name,
    #         "invoice_payment_term_id": mkplc_id.payment_term_id.id,
    #         "payment_reference": False,
    #         "transaction_ids": [(6, 0, [])],
    #         "company_id": order_id.company_id.id,
    #         "invoice_incoterm_id": False
    #     })
    #     inv_vals['invoice_line_ids'] = []
    #
    #     for line in order_id.order_line:
    #         #####################################################################################
    #         #TO DO: Compute Price from Pricelist
    #         #####################################################################################
    #         inv_vals['invoice_line_ids'].append(
    #             (0, 0,
    #              {
    #                  "display_type": False,
    #                  "sequence": 0,
    #                  "name": line.name,
    #                  "product_id": line.product_id.id,
    #                  "product_uom_id": line.product_id.uom_id.id,
    #                  "quantity": line.product_qty,
    #                  "discount": line.discount,
    #                  "price_unit": line.price_unit,
    #                  "tax_ids": [(6, 0, line.tax_id.ids)],
    #                  "analytic_account_id": False,
    #                  "analytic_tag_ids": [(6, 0, [])],
    #                  "sale_line_ids": [(4, 81)]
    #              })
    #         )
    #
    #     self.env['account.move'].sudo().create(inv_vals)


    def _shopify_get_ship(self, ship_line, ma_ins_id):
        ship_value = {}
        ship_value['name'] = ship_line.get('title')
        ship_value['sale_ok'] = False
        ship_value['purchase_ok'] = False
        ship_value['type'] = 'service'
        ship_value['default_code'] = ship_line.get('code')
        categ_id = self.env['product.category'].sudo().search(
            [('name', '=', 'Deliveries')], limit=1)
        ship_value['categ_id'] = categ_id.id
        ship_value['company_id'] = ma_ins_id.company_id.id
        ship_value['responsible_id'] = ma_ins_id.user_id.id
        return ship_value

    def shopify_push_tracking(self):
        SaleOrder = self.env['sale.order'].sudo()
        StkPicking = self.env['stock.picking'].sudo()
        marketplace_instance_id = self._get_instance_id()
        current_date = fields.Datetime.now()
        _logger.info("current_date#===>>>" + str(current_date))
        start_date = current_date.replace(
            hour=0, minute=0, second=0, microsecond=0)
        end_date = current_date.replace(
            hour=23, minute=59, second=59, microsecond=999999)
        _logger.info("start_date#===>>>" + str(start_date))
        _logger.info("end_date#===>>>" + str(end_date))
        log_msg = ''

        if marketplace_instance_id.marketplace_instance_type == 'shopify':
            sale_domain = [('state', 'in', ('sale', 'done')),
                           ('shopify_track_updated', '=', False),
                           ('date_order', '>=', start_date),
                           ('date_order', '<=', end_date)
                           ]
            sale_ids = SaleOrder.search(sale_domain)

            _logger.info("Sale#===>>>" + str(sale_ids))
            for sale_id in sale_ids:
                """Step: 1. Find all Pickings for sale Order"""
                pick_domain = [
                    ('state', '=', 'done'),
                    ('shopify_track_updated', '=', False),
                    ('origin', '=', sale_id.name)]
                pickings = StkPicking.search(pick_domain)
                _logger.info("pickings#===>>>" + str(pickings))
                """Step: 2. If Picking == 1: Update Tracking Number"""
                if len(pickings) == 1:
                    msg = _("Push Tracking for Sale Order-%s, Picking-%s Starts" %
                            (sale_id.name, pickings.name))
                    _logger.info(msg)
                    log_msg += "\n" + msg
                    response = pickings.create_shopify_fulfillment()
                    msg = _("Push Tracking for Sale Order-%s, Picking-%s Ends" %
                            (sale_id.name, pickings.name))
                    _logger.info(msg)
                    log_msg += "\n" + msg
                """Step: 2. If Picking  > 1: Do nothing"""
                if len(pickings) > 1:
                    msg = _("Tracking cannot be updated for Sale Order-%s" %
                            (sale_id.name))
                    _logger.warning(msg)
                    log_msg += "\n" + msg


    def _process_customer_addresses(self, partner_id, item):
        vals = {}
        if type(item['addresses']) == dict:
            if item.get('addresses'):
                for address in item.get('addresses'):
                    if address.get('default') and partner_id.type == 'invoice':
                        partner_id.write({
                            'shopify_default': True,
                            'shopify_add_id': address.get('id'),
                        })
                    if address.get('default') == False:
                        domain = [('shopify_add_id', '=', address.get('id'))]
                        res_partner = self.env['res.partner']
                        part_id = res_partner.sudo().search(domain, limit=1)
                        if not part_id:
                            add_vals = get_address_vals(self.env, address)
                            add_vals['type'] = 'other'
                            add_vals['parent_id'] = partner_id.id
                            add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                            add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id
                        try:
                            with self.env.cr.savepoint():
                                res_partner.sudo().create(add_vals)
                        except Exception as e:
                            _logger.warning("Skip child address create (shopify_add_id=%s): %s", address.get('id'), e)
        elif type(item.get('addresses')) == list:
            for address in item['addresses']:
                if address.get('default') and partner_id.type == 'invoice':
                    partner_id.write({
                        'shopify_default': True,
                        'shopify_add_id': address.get('id'),
                    })
                if address.get('default') == False:
                    domain = [('shopify_add_id', '=', address.get('id'))]
                    res_partner = self.env['res.partner']
                    part_id = res_partner.sudo().search(domain, limit=1)
                    if not part_id:
                        add_vals = get_address_vals(self.env, address)
                        add_vals['type']='other'
                        add_vals['parent_id'] = partner_id.id
                        add_vals['property_account_receivable_id'] = partner_id.property_account_receivable_id.id
                        add_vals['property_account_payable_id'] = partner_id.property_account_payable_id.id
                        try:
                            with self.env.cr.savepoint():
                                res_partner.sudo().create(add_vals)
                        except Exception as e:
                            _logger.warning("Skip child address create (shopify_add_id=%s): %s", address.get('id'), e)

        return vals

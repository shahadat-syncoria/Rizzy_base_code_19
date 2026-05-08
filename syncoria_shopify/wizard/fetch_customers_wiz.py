# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, _
from odoo.http import request
import re
import json
import logging
from ..shopify.utils import parse_gql_nodes, from_shopify_gid

_logger = logging.getLogger(__name__)


class CustomerFetchWizard(models.TransientModel):
    _inherit = 'customer.fetch.wizard'

    shopify_customer_no = fields.Char()

    def cron_shopify_fetch_customers(self, instance_id=None):
        """Cron entrypoint: fetch customers for one/all confirmed Shopify instances."""
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
                wizard = self.create({'instance_id': rec.id})
                wizard.fetch_customers_to_odoo()
            except Exception as e:
                self.env['marketplace.logging'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('marketplace.logging'),
                    'create_uid': self.env.user.id,
                    'marketplace_instance_id': rec.id,
                    'level': 'warning',
                    'type': 'client',
                    'summary': 'Shopify cron customer fetch failed',
                    'error': str(e).replace('<br>', '').replace('</br>', '\n'),
                })

    def create_feed_customer(self, customer_data):
        summary = ''
        error = ''
        feed_customer_id = False
        try:
            domain = [('shopify_id', '=', customer_data['id'])]
            feed_customer_id = self.env['shopify.feed.customers'].sudo().search(domain, limit=1)
            if feed_customer_id:
                feed_customer_id.write({
                    'customer_data': json.dumps(customer_data),
                    'customer_name': customer_data.get('first_name','') + ' ' + customer_data.get('last_name',''),
                    'email': customer_data.get('email'),     
                })
                message =  "Shopify Feed Customer Updated-{}, Customer ID-{}".format(feed_customer_id, customer_data['id'])
                summary += '\n' + message
                feed_customer_id.message_post(body=message)
                _logger.info(message)

            if not feed_customer_id:
                feed_customer_id = self.env['shopify.feed.customers'].sudo().create({
                    'name': self.env['ir.sequence'].next_by_code('shopify.feed.customers'),
                    'instance_id': self.instance_id.id,
                    'shopify_id': customer_data['id'],
                    'customer_data': json.dumps(customer_data),
                    'state': 'draft',
                    'customer_name': customer_data.get('first_name','') + ' ' + customer_data.get('last_name',''),
                    'email': customer_data.get('email', ''),
                    'country_name': customer_data.get('country_name', ''),
                })
                feed_customer_id.env.cr.commit()
                message =  "Shopify Feed Customer Created-{}, Customer ID-{}".format(feed_customer_id, customer_data['id'])
                summary += '\n' + message
                _logger.info(message)

        except Exception as e:
            message = str(e.args)
            summary += '\n' + message
            error += '\n' + message
            _logger.warning("Exception-{}".format(e.args))
        return feed_customer_id, summary, error

    def shopify_fetch_customers_to_odoo(self, kwargs=None):
        """Fetch customers: res.partner / Shopify mapping (contact, invoice, etc.)."""
        kwargs = kwargs or {}

        PartnerObj = self.env['res.partner']
        cr = self.env.cr

        marketplace_instance_id = kwargs.get('marketplace_instance_id')
        if marketplace_instance_id:
            use_graphql = getattr(marketplace_instance_id, "use_graphql", False)

            if not use_graphql:
                raise exceptions.UserError(
                    _("This fetch is GraphQL-only. Enable 'Use GraphQL' on the Shopify instance.")
                )

            shopify_customer_id = (self.shopify_customer_no or "").strip()
            _logger.info(
                "Shopify fetch customers (GraphQL): instance=%s customer_id=%s dates=%s..%s",
                marketplace_instance_id.id,
                shopify_customer_id or "all",
                self.date_from or "-",
                self.date_to or "-",
            )

            headers = {'X-Service-Key': marketplace_instance_id.token}
            items = []
            customer_list = {}
            if use_graphql:
                def _addr(address):
                    if not address:
                        return {}
                    return {
                        "id": from_shopify_gid(address.get("id")),
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
                        "default": bool(address.get("default")),
                    }

                def _normalize(node):
                    addresses = [_addr(a) for a in parse_gql_nodes(node, ("addressesV2",))]
                    default_address = _addr((node or {}).get("defaultAddress"))
                    return {
                        "id": from_shopify_gid((node or {}).get("id")),
                        "first_name": (node or {}).get("firstName"),
                        "last_name": (node or {}).get("lastName"),
                        "email": (node or {}).get("email"),
                        "phone": (node or {}).get("phone"),
                        "state": ((node or {}).get("state") or "").lower() or None,
                        "note": (node or {}).get("note"),
                        "orders_count": (node or {}).get("numberOfOrders"),
                        "verified_email": (node or {}).get("verifiedEmail"),
                        "tax_exempt": (node or {}).get("taxExempt"),
                        "tags": ",".join((node or {}).get("tags") or []),
                        "default_address": default_address if default_address else None,
                        "addresses": addresses,
                    }

                if shopify_customer_id:
                    query = """
                    query SyncoriaCustomerById($id: ID!) {
                      customer(id: $id) {
                        id firstName lastName email phone state note numberOfOrders verifiedEmail taxExempt tags
                        defaultAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                        addressesV2(first: 250) {
                          nodes { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                        }
                      }
                    }
                    """
                    customer_list, _next = self.env['marketplace.connector'].shopify_graphql_call(
                        headers=headers,
                        url='/graphql.json',
                        query=query,
                        variables={"id": "gid://shopify/Customer/%s" % shopify_customer_id},
                        type='POST',
                        marketplace_instance_id=marketplace_instance_id,
                    )
                    node = (customer_list.get("data") or {}).get("customer")
                    if node:
                        items.append(_normalize(node))
                else:
                    query = """
                    query SyncoriaCustomers($first: Int!, $after: String, $query: String, $sortKey: CustomerSortKeys!) {
                      customers(first: $first, after: $after, query: $query, sortKey: $sortKey) {
                        edges {
                          node {
                            id firstName lastName email phone state note numberOfOrders verifiedEmail taxExempt tags
                            defaultAddress { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                            addressesV2(first: 250) {
                              nodes { id address1 address2 city company firstName lastName phone province country zip name provinceCode countryCodeV2 }
                            }
                          }
                        }
                        pageInfo { hasNextPage endCursor }
                      }
                    }
                    """
                    query_filter = []
                    # Customer list search: use account creation window (not last profile update).
                    if self.date_from:
                        query_filter.append("created_at:>=%s" % self.date_from.strftime("%Y-%m-%d"))
                    if self.date_to:
                        query_filter.append("created_at:<=%s" % self.date_to.strftime("%Y-%m-%d"))
                    sort_key = "CREATED_AT" if (self.date_from or self.date_to) else "UPDATED_AT"
                    after = None
                    while True:
                        customer_list, _next = self.env['marketplace.connector'].shopify_graphql_call(
                            headers=headers,
                            url='/graphql.json',
                            query=query,
                            variables={
                                "first": 250,
                                "after": after,
                                "query": " ".join(query_filter) or None,
                                "sortKey": sort_key,
                            },
                            type='POST',
                            marketplace_instance_id=marketplace_instance_id,
                        )
                        for node in parse_gql_nodes(customer_list.get("data") or {}, ("customers",)):
                            items.append(_normalize(node))
                        page_info = ((customer_list.get("data") or {}).get("customers") or {}).get("pageInfo") or {}
                        if not page_info.get("hasNextPage"):
                            break
                        after = page_info.get("endCursor")
            # REST path intentionally removed (GraphQL-only).

            try:
                cr.execute("select shopify_id from res_partner "
                           "where shopify_id is not null")
                partners = cr.fetchall()
                partner_ids = [i[0] for i in partners] if partners else []

                # need to fetch the complete required fields list
                # and their values

                cr.execute("select id from ir_model "
                           "where model='res.partner'")
                partner_model = cr.fetchone()

                if not partner_model:
                    return
                cr.execute("select name from ir_model_fields "
                           "where model_id=%s and required=True ",
                           (partner_model[0],))
                res = cr.fetchall()
                fields_list = [i[0] for i in res if res] or []
                partner_vals = PartnerObj.default_get(fields_list)


                for i in items:
                    try:
                        # Keep each customer isolated; one bad row must not abort full sync transaction.
                        with self.env.cr.savepoint():
                            if str(i['id']) not in partner_ids:
                                customer_id = self.shopify_find_customer_id(
                                    i,
                                    partner_ids,
                                    partner_vals,
                                    main=True
                                )

                                if customer_id:
                                    PartnerObj.browse(customer_id).write({"marketplace_instance_id": marketplace_instance_id.id})
                                    _logger.info(
                                        "Customer is created with id %s", customer_id)
                                else:
                                    _logger.info("Unable to create Customer")
                            else:

                                partner = PartnerObj.search([("shopify_id", "=", i['id'])], limit=1)
                                partner.write({"marketplace_instance_id": marketplace_instance_id.id})
                                tags = (i.get('tags') or "").split(",")
                                try:
                                    tag_ids = []
                                    for tag in tags:
                                        tag_id = self.env['res.partner.category'].search([("name", "=", tag)], limit=1)
                                        if not tag_id and tag != "":
                                            tag_id = self.env['res.partner.category'].create(
                                                {"name": tag, "color": 1, "active": True}
                                            )
                                            # current_order_id.write({"tag_ids":[(0,0, {"name": tag, "color": 1}))
                                        if tag_id:
                                            tag_ids.append(tag_id.id)
                                    if tag_ids:
                                        partner.category_id = tag_ids
                                    else:
                                        partner.category_id.unlink()
                                except Exception as e:
                                    _logger.warning(e)
                    except Exception as e:
                        _logger.warning("Skipping customer %s due to error: %s", i.get('id'), e)

                if 'call_button' in str(request.httprequest):
                    return {
                        'name': ('Shopify Customers'),
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'list,form',
                        'res_model': 'res.partner',
                        'view_id': False,
                        'domain': [('marketplace_type', '=', 'shopify')],
                        'target': 'current',
                    }
                return {
                    'type': 'ir.actions.client',
                    'tag': 'reload'
                }

            except Exception as e:
                if customer_list.get('errors'):
                    e = customer_list.get('errors')
                _logger.info("Exception occured: %s", e)
                raise exceptions.UserError(_("Error Occured: %s") % e)

    def shopify_find_customer_id(self, order, ids, partner_vals, main=False):
        # order-->order
        # main-->True: Fetch Customers
        # main-->False: Fetch Orders

        item = order if main else order
        cr = self.env.cr
        id_key = 'id'
        item_id_key = item.get(id_key) if main else order.get(
            'customer', {}).get('id')
        res = None
        if item_id_key and \
                str(item_id_key) in ids:
            cr.execute("select id from res_partner "
                       "where shopify_id=%s",
                       (str(item_id_key),))
            res = cr.fetchone()
            return res and res[0] or None
        else:
            if not main:
                try:
                    partner_vals = get_customer_vals(
                        self, id_key, item, partner_vals)
                except Exception as e:
                    _logger.warning("\nshopify_find_customer_id===>" + str(e))

            child_ids = []
            if main:
                res_partner = self.env['res.partner'].sudo()
                # Link an existing Odoo contact by email when it isn't already linked to Shopify.
                # Note: `shopify_id` is often NULL/False (not empty string), so match both.
                partner_id = res_partner.search(
                    [
                        '&',
                        ('email', '=', item.get('email')),
                        '|',
                        ('shopify_id', '=', False),
                        ('shopify_id', '=', ''),
                    ],
                    limit=1
                )

                _logger.warning("\nPartner with Email===>>>%s exists", item.get('email'))
                if partner_id:
                    # Need to check Customer Addresses
                    # Merge Shopify values onto required defaults to avoid missing required fields.
                    shopify_vals = ShopifyCustomer(item, self.env)._partner_vals
                    merged_vals = dict(partner_vals or {})
                    merged_vals.update(shopify_vals or {})
                    partner_id.update(merged_vals)
                    self._process_customer_addresses(partner_id, item)
                    return partner_id.id

                # Merge Shopify values onto required defaults to avoid missing required fields.
                shopify_vals = ShopifyCustomer(item, self.env)._partner_vals
                merged_vals = dict(partner_vals or {})
                merged_vals.update(shopify_vals or {})
                partner_vals = merged_vals
                if 'child_ids' in partner_vals:
                    child_ids = partner_vals.get('child_ids')
                    del (partner_vals['child_ids'])

            if partner_vals.get('shopify_id'):
                # Some deployments have extra NOT NULL custom fields on `res.partner`.
                # Only include these keys when the fields exist in this DB schema.
                partner_fields = self.env['res.partner']._fields
                for optional_key in ('group_rfq', 'group_on'):
                    if optional_key in partner_vals and optional_key not in partner_fields:
                        partner_vals.pop(optional_key, None)
                if 'group_rfq' in partner_fields:
                    partner_vals.setdefault('group_rfq', False)
                if 'group_on' in partner_fields:
                    partner_vals.setdefault('group_on', False)
                query_cols = self.fetch_query(partner_vals)
                query_str = "insert into res_partner (" + \
                            query_cols + ") values %s RETURNING id"
                try:
                    # Isolate raw INSERT failures so the surrounding transaction remains usable.
                    with self.env.cr.savepoint():
                        cr.execute(query_str, (tuple(partner_vals.values()),))
                        res = cr.fetchone()
                except Exception as e:
                    _logger.warning("Skip partner create for Shopify customer %s: %s", item.get('id'), e)
                    return None

                if res:
                    partner = self.env['res.partner'].sudo().search([('id', '=', res[0])])
                    self._process_customer_tags(partner, item)
                    if len(child_ids) > 0:
                        _logger.info("Partner ===>>>", partner)
                        partner.write({'child_ids': child_ids})

        return res and res[0] or None

    def _process_customer_tags(self, partner_id, values):
        if values.get("tags"):
            splited_tags = values.get("tags").split(',')
            res_partner_cat = self.env['res.partner.category']
            for tags in splited_tags:
                existing_tags = res_partner_cat.search([("name", "=", tags)], limit=1)
                if existing_tags:
                    partner_id.write({'category_id': [(4, existing_tags.id)]})
                else:
                    # new_tag=res_partner_cat.create({"name":tags,"color":1,"active":True,"parent_id":env.ref("syncoria_shopify.shopify_tag").id})
                    # self._partner_vals['category_id'] = new_tag.id
                    if tags != "":
                        partner_id.write({'category_id': [(0, 0, {"name": tags, "color": 1, "active": True})]})


class ShopifyCustomer:
    def __init__(self, values, env, shipping=False):
        self._partner_vals={}
        self._partner_vals['child_ids'] = []
        self._partner_vals['name']=(values.get(
            'first_name') or "") + " " + (values.get('last_name') or "")
        self._partner_vals['autopost_bills'] = 'ask'
        self._partner_vals['complete_name']=self._partner_vals['name']
        self._partner_vals['phone']=values.get('phone') or ""
        self._partner_vals['email']=values.get('email') or ""
        self._partner_vals['shopify_id']=values.get('id') or ""
        self._partner_vals['marketplace_type']='shopify'
        self._partner_vals['active']=True
        self._partner_vals['type']='invoice'
        # Optional custom fields: only set if present in this DB schema.
        partner_fields = env['res.partner']._fields
        if 'group_rfq' in partner_fields:
            self._partner_vals['group_rfq'] = False
        if 'group_on' in partner_fields:
            self._partner_vals['group_on'] = False
        self._partner_vals['shopify_accepts_marketing']=values.get(
            'shopify_accepts_marketing')
        self._partner_vals['shopify_last_order_id']=values.get(
            'last_order_id')
        self._partner_vals['shopify_last_order_name']=values.get(
            'last_order_name')
        self._partner_vals['marketing_opt_in_level']=values.get(
            'marketing_opt_in_level')
        self._partner_vals['multipass_identifier']=values.get(
            'multipass_identifier')
        self._partner_vals['orders_count']=values.get('orders_count')
        self._partner_vals['shopify_state']=values.get('state')
        self._partner_vals['comment']=values.get('note')
        self._partner_vals['shopify_tax_exempt']=values.get('tax_exempt')
        exempt_ids=[]
        if values.get('tax_exempt'):
            for exempt in values.get('tax_exemptions'):
                SpTaxExempt=self.env['shopify.tax.exempt']
                exempt_id=SpTaxExempt.sudo().search(
                    [('name', '=', exempt)], limit=1)
                exempt_ids.append(exempt_id.id) if exempt_id else None
            # self._partner_vals['shopify_tax_exemptions_ids'] = exempt_ids

        self._partner_vals['shopify_total_spent']=values.get(
            'total_spent')
        self._partner_vals['shopify_verified_email']=values.get(
            'verified_email')

        # Handle Company
        # Handle Different Type of Addresses
        self._process_addresses(env, values)

    def _process_addresses(self, env, values):
        ############Default Address Starts####################################
        if values.get('default_address') or values.get('addresses'):
            default_address=values.get(
                'default_address') or values.get('addresses')[0]
        else:
            default_address=values
        country=False
        state=False

        if default_address:
            # self._handle_company(default_address)
            if default_address.get('company'):
                company = env['res.partner'].sudo().search(
                    [('name', '=', default_address.get('company')), ('is_company', '=', True)], limit=1)
                self._partner_vals['parent_id']=company.id if company else None
                self._partner_vals['company_name']=default_address.get(
                    'company') or ""

            self._partner_vals['street']=default_address.get(
                'address1') or ""
            self._partner_vals['street2']=default_address.get(
                'address2') or ""
            self._partner_vals['city']=default_address.get('city') or ""

            search_domain=[]
            if default_address.get('country_code'):
                search_domain += [('code', '=',
                                default_address.get('country_code'))]
                # country = env['res.country'].sudo().search(
                #     [('code', '=', default_address.get('country_code'))], limit=1)
            elif default_address.get('country'):
                search_domain += [('name', '=',
                                default_address.get('country'))]
                # country = env['res.country'].sudo().search(
                #     [('name', '=', default_address.get('country'))], limit=1)
            country=env['res.country'].sudo().search(search_domain, limit=1)
            self._partner_vals['country_id']=country.id if country else None
            state_domain=[('country_id', '=', country.id)] if country else []
            if default_address.get('province_code'):
                state_domain += [('code', '=',
                                default_address.get('province_code'))]
                # state = env['res.country.state'].sudo().search(
                #     [('code', '=', default_address.get('province_code'))], limit=1)
            elif default_address.get('province'):
                search_domain += [('name', '=',
                                default_address.get('province'))]
                # state = env['res.country.state'].sudo().search(
                #     [('name', '=', default_address.get('province'))], limit=1)
            state=env['res.country.state'].sudo().search(
                state_domain, limit=1)

            self._partner_vals['state_id']=state.id if state else None
            self._partner_vals['zip']=default_address.get('zip') or ""

        # if values.get('addresses'):
        #     if len(values.get('addresses')) > 1:
        #         for address in values.get('addresses'):
        #             if not address.get('default'):
        #                 add_vals = get_address_vals(env, address)
        #                 self._partner_vals['child_ids'].append((0, 0, add_vals))
        ############Default Address Ends####################################


    def _handle_company(self, env, address):
        vals={}
        if address.get('company'):
            domain=[('name', '=', address.get('company'))]
            domain += [('is_company', '=', True)]
            company=env['res.partner'].sudo().search(domain, limit=1)
            address['parent_id']=company.id if company else None
            address['company_name']=address.get('company', '')
        return vals
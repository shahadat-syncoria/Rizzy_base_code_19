# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

from odoo import models, fields, exceptions, api, _
import logging
_logger = logging.getLogger(__name__)


class SaleOrderSExtend(models.Model):
    _inherit = 'sale.order'

    def fix_delivery_address(self):
        res_country = self.env['res.country'].sudo()
        res_country_state = self.env['res.country.state'].sudo()
        if self.shopify_instance_id and self.shopify_id:
            marketplace_instance_id = self.shopify_instance_id
            sp_order_dict = {}
            if getattr(marketplace_instance_id, "use_graphql", False):
                # Fetch order addresses via GraphQL (preferred)
                query = """
                query SyncoriaOrderAddresses($id: ID!) {
                  order(id: $id) {
                    email
                    phone
                    contactEmail
                    billingAddress {
                      name
                      address1
                      address2
                      city
                      zip
                      province
                      country
                      phone
                    }
                    shippingAddress {
                      name
                      address1
                      address2
                      city
                      zip
                      province
                      country
                      phone
                    }
                  }
                }
                """
                res, _next = self.env['marketplace.connector'].shopify_graphql_call(
                    headers={'X-Service-Key': marketplace_instance_id.token},
                    url='/graphql.json',
                    query=query,
                    variables={"id": "gid://shopify/Order/%s" % self.shopify_id},
                    type='POST',
                    marketplace_instance_id=marketplace_instance_id,
                )
                if res.get("errors"):
                    _logger.warning("Shopify GraphQL order fetch errors: %s", res.get("errors"))
                    sp_order_dict = {}
                else:
                    order = (res.get("data") or {}).get("order") or {}
                    # normalize to the same dict shape used below
                    sp_order_dict = {
                        "contact_email": order.get("contactEmail") or order.get("email"),
                        "email": order.get("email"),
                        "phone": order.get("phone"),
                        "billing_address": order.get("billingAddress") or {},
                        "shipping_address": order.get("shippingAddress") or {},
                    }
            else:
                raise exceptions.UserError(_("GraphQL-only: enable 'Use GraphQL' on the Shopify instance."))

            if sp_order_dict:
                    partner_id = self.partner_id
                    partner_invoice_id = self.partner_invoice_id
                    partner_shipping_id = self.partner_shipping_id
                    
                    if sp_order_dict.get('contact_email'):
                        parner_vals = {
                            'email': sp_order_dict.get('contact_email') or sp_order_dict.get('email'),
                            'phone': sp_order_dict.get('phone'),
                        }
                        partner_id.write(parner_vals)


                    if sp_order_dict.get('billing_address'):
                        billing_address = sp_order_dict.get('billing_address', {})

                        if partner_invoice_id:
                            country_id = self.env['res.country'].sudo()
                            state_id = self.env['res.country.state'].sudo()

                            if billing_address.get('country'):
                                bill_country = billing_address.get('country')
                                country_domain = [('name', '=', bill_country)]
                                country_id = res_country.search(country_domain, limit=1)

                            if billing_address.get('province'):
                                state_domain = [('country_id', '=', country_id.id)] if country_id else []
                                state_domain += [('name', '=', billing_address.get('province'))]
                                state_id = res_country_state.search(state_domain, limit=1)

                            partner_invoice_id.write({
                                'name': billing_address.get('name', None),
                                'street': billing_address.get('address1'),
                                'street2': billing_address.get('address2'),
                                'city': billing_address.get('city'),
                                'zip': billing_address.get('zip'),
                                'state_id': state_id.id,
                                'country_id': country_id.id,
                                'phone': billing_address.get('phone'),
                            })

                    if sp_order_dict.get('shipping_address'):
                        shipping_address = sp_order_dict.get('shipping_address', {})

                        if partner_shipping_id:
                            country_id = self.env['res.country'].sudo()
                            state_id = self.env['res.country.state'].sudo()

                            if shipping_address.get('country'):
                                bill_country = shipping_address.get('country')
                                country_domain = [('name', '=', bill_country)]
                                country_id = res_country.search(country_domain, limit=1)

                            if shipping_address.get('province'):
                                state_domain = [('country_id', '=', country_id.id)] if country_id else []
                                state_domain += [('name', '=', shipping_address.get('province'))]
                                state_id = res_country_state.search(state_domain, limit=1)

                            partner_shipping_id.write({
                                'name': shipping_address.get('name', None),
                                'street': shipping_address.get('address1'),
                                'street2': shipping_address.get('address2'),
                                'city': shipping_address.get('city'),
                                'zip': shipping_address.get('zip'),
                                'state_id': state_id.id,
                                'country_id': country_id.id,
                                'phone': shipping_address.get('phone'),
                            })

            else:
                error = """No Shopify Order Found"""
                _logger.warning(error)
        else:
            error = "shopify_instance_id or shopify_id are missing for SO-{}".format(self.name)
            _logger.warning(error)
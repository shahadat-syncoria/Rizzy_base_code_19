# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################

import pprint
import uuid
from urllib.parse import urlencode
from odoo import models, fields, api, _
from odoo.http import request
import requests
from odoo.exceptions import UserError, ValidationError

import logging
_logger = logging.getLogger(__name__)

# Single source of truth for OAuth — keep in sync with scopes enabled on the Shopify app.
SHOPIFY_OAUTH_SCOPES = (
    "read_products,write_products,read_inventory,write_inventory,"
    "read_customers,write_customers,read_orders,write_orders,"
    "read_all_orders,"
    "read_fulfillments,write_fulfillments,read_locations,"
    "read_merchant_managed_fulfillment_orders,write_merchant_managed_fulfillment_orders"
)


def _normalize_shopify_host(value):
    """Strip URL noise; if the user typed only the store slug, append .myshopify.com."""
    if not value:
        return value
    host = str(value).replace("https://", "").replace("http://", "").strip().rstrip("/")
    if "." not in host:
        host = "%s.myshopify.com" % host
    return host


class ModelName(models.Model):
    _inherit = 'marketplace.instance'
    apply_tax = fields.Boolean(string='Apply Tax', default=True)
    marketplace_app_id = fields.Integer(string='App ID',default=0)
    marketplace_instance_type = fields.Selection(selection_add=[('shopify', 'Shopify')], default='shopify')
    marketplace_api_key = fields.Char(string='API key')
    marketplace_api_password = fields.Char(string='Password')
    marketplace_secret_key = fields.Char(string='Secret Key')
    marketplace_host = fields.Char(string='Host')
    shopify_auth_mode = fields.Selection(
        [('direct_oauth', 'Direct OAuth (Per Store)')],
        string='Auth Mode',
        default='direct_oauth',
        required=True,
        help="Recommended for new customers: Direct OAuth (Per Store).",
    )
    shopify_oauth_token = fields.Char(string='OAuth Access Token', copy=False, password=True)
    shopify_oauth_state = fields.Char(string='OAuth State', copy=False)
    shopify_is_oauth_connected = fields.Boolean(
        string='OAuth Connected',
        compute='_compute_shopify_oauth_connected',
    )
    shopify_oauth_callback_url = fields.Char(
        string='OAuth Callback URL',
        compute='_compute_shopify_oauth_callback_url',
    )
    shopify_oauth_scopes = fields.Char(
        string='OAuth Scopes',
        default=SHOPIFY_OAUTH_SCOPES,
        help='Technical copy of required scopes (install URLs always use the built-in list).',
    )
    marketplace_webhook = fields.Boolean(
        string='Use Webhook?',
    )
    default_res_partner_id = fields.Many2one('res.partner', string='Default Contact For Order With No Customer')
    @api.onchange('marketplace_host')
    def _onchange_marketplace_host(self):
        if self.marketplace_host and self.marketplace_instance_type == 'shopify':
            self.marketplace_host = _normalize_shopify_host(self.marketplace_host)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("marketplace_instance_type") == "shopify":
                vals["use_graphql"] = True
                if vals.get("marketplace_host"):
                    vals["marketplace_host"] = _normalize_shopify_host(vals["marketplace_host"])
        return super().create(vals_list)

    def write(self, vals):
        vals = dict(vals)
        shopify_recs = self.filtered(lambda r: r.marketplace_instance_type == "shopify")
        if shopify_recs and vals.get("use_graphql") is False:
            vals.pop("use_graphql")
        if (
            vals.get("marketplace_host")
            and len(shopify_recs) == len(self)
        ):
            vals["marketplace_host"] = _normalize_shopify_host(vals["marketplace_host"])
        return super().write(vals)

    @api.depends('shopify_oauth_token')
    def _compute_shopify_oauth_connected(self):
        for rec in self:
            rec.shopify_is_oauth_connected = bool(rec.shopify_oauth_token)

    def _compute_shopify_oauth_callback_url(self):
        icp_sudo = self.env['ir.config_parameter'].sudo()
        base_url = (icp_sudo.get_param('web.base.url') or '').rstrip('/')
        for rec in self:
            rec.shopify_oauth_callback_url = "%s/shopify/oauth/callback" % base_url
    
    marketplace_is_shopify = fields.Boolean(compute='_compute_is_shopify' )
    
    @api.depends('marketplace_instance_type')
    def _compute_is_shopify(self):
        for record in self:
            record.marketplace_is_shopify = False
            if record.marketplace_instance_type == 'shopify':
                record.marketplace_is_shopify = True

    marketplace_api_version = fields.Char(
        string='Api Version',
        default="2026-04"
    )
    use_graphql = fields.Boolean(
        string='Use GraphQL',
        default=True,
        help="Shopify connectivity uses GraphQL; this stays enabled.",
    )

    marketplace_payment_journal_id  = fields.Many2one(
        string='Payment Journal',
        comodel_name='account.journal',
        ondelete='restrict',
    )
    marketplace_refund_journal_id = fields.Many2one(
        string='Refund Journal',
        comodel_name='account.journal',
        ondelete='restrict'
    )
    marketplace_inbound_method_id  = fields.Many2one(
        string='Inbound Payment Method',
        comodel_name='account.payment.method',
        ondelete='restrict',
        domain=[('payment_type','=','inbound')]
    )
    marketplace_outbound_method_id  = fields.Many2one(
        string='Outbound Payment Method',
        comodel_name='account.payment.method',
        ondelete='restrict',
        domain=[('payment_type','=','outbound')]
    )
    refund_discrepancy_account_id = fields.Many2one('account.account', string='Refund Discrepancy Account')

    shopify_payment_method_mappings = fields.One2many('shopify.payment.method.mappings', 'shopify_instance_id', string='Payment method mappings')
    shopify_refund_payment_method_mappings = fields.One2many('shopify.refund.payment.method.mappings', 'shopify_instance_id', string='Refund Payment method mappings')
    shopify_shipping_method_mappings = fields.One2many('shopify.shipping.method.mappings', 'shopify_instance_id', string='Shipping method mappings')
    is_product_create = fields.Boolean(string="Enable New product creation",default=True,help="While fetching the product if enabled new product will be created otherwise only update existing products")
    is_sku = fields.Boolean(default=False)
    product_mapping = fields.Selection([
        ('barcode', 'By Barcode'),
        ('sku', 'By SKU')
    ], string="Product Mapping", default='sku')
    delivery_product_id = fields.Many2one('product.product', string="Delivery Product")
    tax_group_id = fields.Many2one('account.tax.group', string="Account Tax Group")
    # debit_account_id = fields.Many2one(
    #     comodel_name='account.account',
    #     string='Debit Account',
    #     store=True, readonly=False,
    #     # domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
    #     check_company=True)#	Current Assets
    # credit_account_id = fields.Many2one(
    #     comodel_name='account.account',
    #     string='Credit Account',
    #     store=True, readonly=False,
    #     domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
    #     check_company=True)#receivable


    ##############################################################################################################
    compute_pricelist_price = fields.Boolean(default=True)
    ##############################################################################################################

    # destination_account_id = fields.Many2one(
    #     comodel_name='account.account',
    #     string='Destination Account',
    #     store=True, readonly=False,
    #     compute='_compute_destination_account_id',
    #     domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",
    #     check_company=True)
    
    # @api.depends('journal_id', 'partner_id', 'partner_type', 'is_internal_transfer')
    # def _compute_destination_account_id(self):
    #     self.destination_account_id = False
    #     for pay in self:
    #         if pay.is_internal_transfer:
    #             pay.destination_account_id = pay.journal_id.company_id.transfer_account_id
    #         elif pay.partner_type == 'customer':
    #             # Receive money from invoice or send money to refund it.
    #             if pay.partner_id:
    #                 pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_receivable_id
    #             else:
    #                 pay.destination_account_id = self.env['account.account'].search([
    #                     ('company_id', '=', pay.company_id.id),
    #                     ('internal_type', '=', 'receivable'),
    #                     ('deprecated', '=', False),
    #                 ], limit=1)
    #         elif pay.partner_type == 'supplier':
    #             # Send money to pay a bill or receive money to refund it.
    #             if pay.partner_id:
    #                 pay.destination_account_id = pay.partner_id.with_company(pay.company_id).property_account_payable_id
    #             else:
    #                 pay.destination_account_id = self.env['account.account'].search([
    #                     ('company_id', '=', pay.company_id.id),
    #                     ('internal_type', '=', 'payable'),
    #                     ('deprecated', '=', False),
    #                 ], limit=1)

    # payment_type = fields.Selection([
    #     ('use_gateway', 'Use Gateway'),
    #     ('use_tag', 'Use Tag')
    # ], string="Choose method to identify account journal", default="use_gateway")

    # payment_journal_ids = fields.One2many('shopify.payment.journal', 'marketplace_instance_id', 'Journal Payments')
    # apply_payment_immediate = fields.Boolean('Apply payment immediately when order is created', default=False)
    @api.onchange('auto_create_product')
    def _onchange_auto_create_product(self):
        for rec in self:
            if rec.auto_create_product:
                rec.is_product_create = True
                rec.message_notify(body="New product creation Enabled also!")




    def action_check_access(self):
        if not self.token:
            raise UserError(_("Missing Omnisync Service Key in this instance. Please sync subscriptions first."))
        if not self.shopify_oauth_token:
            raise UserError(_("Please authorize this instance first using 'Authorize Shopify'."))
        connection_query = """
        query SyncoriaConnectionTest {
          shop {
            id
            name
          }
          appInstallation {
            accessScopes {
              handle
            }
          }
        }
        """
        access, next_link = self._shopify_graphql_call(connection_query, {})
        has_shop = (access.get('data') or {}).get('shop')
        has_scopes = bool(((access.get('data') or {}).get('appInstallation') or {}).get('accessScopes'))
        if has_shop or has_scopes:
            msg =_("Store Acess Connection Successful for Marketplace-%s" %(self.name))
            if self.marketplace_state != 'confirm':
                self.write({'marketplace_state' : 'confirm'})
            
        else:
            msg =_("Store Acess Connection Failed for Marketplace-%s" %(self.name))
        _logger.info(msg)
        self.message_post(body=msg)

    def _shopify_oauth_callback_url(self):
        self.ensure_one()
        icp_sudo = self.env['ir.config_parameter'].sudo()
        base_url = icp_sudo.get_param('web.base.url')
        return "%s/shopify/oauth/callback" % (base_url.rstrip('/'))

    def action_shopify_authorize(self):
        self.ensure_one()
        if self.marketplace_instance_type == "shopify" and not self.use_graphql:
            super(ModelName, self).write({"use_graphql": True})
        if not self.token:
            raise UserError(_("Missing Omnisync Service Key in this instance. Please sync subscriptions first."))
        if not self.marketplace_api_key or not self.marketplace_secret_key or not self.marketplace_host:
            raise UserError(
                _(
                    "Enter your Shopify app Client ID, Client Secret, and store host "
                    "(e.g. mystore — .myshopify.com is added automatically)."
                )
            )
        host = _normalize_shopify_host(self.marketplace_host)
        if host != self.marketplace_host:
            self.marketplace_host = host
        if not host.endswith('.myshopify.com'):
            raise UserError(_("Host must be a valid myshopify domain (e.g. store.myshopify.com)."))
        self.shopify_oauth_state = uuid.uuid4().hex
        callback_url = self._shopify_oauth_callback_url()
        params = {
            'client_id': self.marketplace_api_key,
            'scope': SHOPIFY_OAUTH_SCOPES,
            'redirect_uri': callback_url,
            'state': self.shopify_oauth_state,
        }
        auth_url = "https://%s/admin/oauth/authorize?%s" % (host, urlencode(params))
        return {'type': 'ir.actions.act_url', 'url': auth_url, 'target': 'new'}

    
    def action_cancel_state(self):
        msg =_("Store Acess Connection Disconnected for Marketplace-%s" %(self.name))
        self.write({'marketplace_state' : 'draft'})
        self.message_post(body=msg)
    

    ###########################################################################################
    ################################WEBHOOK####################################################
    ###########################################################################################

    # def action_activate_webhook(self):
    #     _logger.info("action_activate_webhook===>>>>")
    #     url = self.marketplace_host + "admin/api/%s/webhooks.json" %(self.marketplace_api_version)
    #     access,next_link = self.env['marketplace.connector'].shopify_api_call(
    #         headers={'X-Service-Key': self.token},
    #         url=url,
    #         type='GET')

    #     if access.get('webhooks'):
    #         msg =_("Webhooks for Marketplace-%s" %(self.name))
    #         topics = ["orders/create"]

    #         for topic in topics:
    #             """WEBHOOKS FOR SHOPIFY"""
    #             icp_sudo = self.env['ir.config_parameter'].sudo()
    #             base_url =  icp_sudo.get_param('web.base.url')    
    #             _logger.info("base_url ===>>>> %s", base_url)   
    #             data = {
    #                 "webhook": {
    #                     "topic": "orders/create",
    #                     "address": base_url,
    #                     "format": "json"
    #                 }
    #             }

    #             _logger.info("data ===>>>> %s", data)
    #             webhooks,next_link = self.env['marketplace.connector'].shopify_api_call(
    #                 headers={'X-Service-Key': self.token,
    #                         'Content-Type': 'application/json'
    #                 },
    #                 url=url,
    #                 data=data,
    #                 type='POST')


    #             _logger.info("webhooks ===>>>>%s", webhooks)

    #             if webhooks.get('errors'):
    #                 raise UserError(_("Error-%s", str(webhooks.get('errors'))))
    #             else:
    #                 msg =_("Webhooks Successfully Created for-%s" %(self.name))
  
    #     else:
    #         msg =_("Webhooks Failed for Marketplace-%s" %(self.name))
    #     _logger.info(msg)

        
    #     # self.message_post(body=msg)


    def _shopify_graphql_call(self, query, variables=None):
        return self.env['marketplace.connector'].shopify_graphql_call(
            headers={'X-Service-Key': self.token},
            url='/graphql.json',
            query=query,
            variables=variables or {},
            type='POST',
            marketplace_instance_id=self,
        )

    def action_remove_webhook(self):
        res = self.shopify_webhook_request('fetch')
        webhook_edges = ((((res or {}).get('data') or {}).get('webhookSubscriptions') or {}).get('edges') or [])
        wbhk_ids = [((edge or {}).get('node') or {}).get('id') for edge in webhook_edges]
        for wbhk in [w for w in wbhk_ids if w]:
            delete_query = """
            mutation SyncoriaWebhookDelete($id: ID!) {
              webhookSubscriptionDelete(id: $id) {
                deletedWebhookSubscriptionId
                userErrors {
                  field
                  message
                }
              }
            }
            """
            delete_res, _next_link = self._shopify_graphql_call(delete_query, {"id": wbhk})
            payload = ((delete_res.get('data') or {}).get('webhookSubscriptionDelete') or {})
            if payload.get('userErrors'):
                _logger.warning("Webhook delete userErrors: %s", payload.get('userErrors'))
            elif payload.get('deletedWebhookSubscriptionId'):
                _logger.info("Webhook has been successfully deleted! id=%s", payload.get('deletedWebhookSubscriptionId'))


    def shopify_webhook_request(self, r_type):
        if r_type == 'fetch':
            query = """
            query SyncoriaWebhookList {
              webhookSubscriptions(first: 250) {
                edges {
                  node {
                    id
                    topic
                  }
                }
              }
            }
            """
            res, _next_link = self._shopify_graphql_call(query, {})
            return res
        if r_type == 'create':
            icp_sudo = self.env['ir.config_parameter'].sudo()
            callback_url = icp_sudo.get_param('web.base.url')
            query = """
            mutation SyncoriaWebhookCreate($topic: WebhookSubscriptionTopic!, $callbackUrl: URL!) {
              webhookSubscriptionCreate(
                topic: $topic,
                webhookSubscription: {
                  callbackUrl: $callbackUrl,
                  format: JSON
                }
              ) {
                webhookSubscription {
                  id
                }
                userErrors {
                  field
                  message
                }
              }
            }
            """
            res, _next_link = self._shopify_graphql_call(query, {
                "topic": "ORDERS_CREATE",
                "callbackUrl": callback_url,
            })
            return res
        return {"errors": _("Unsupported webhook request type: %s") % r_type}



    color = fields.Integer(default=10)
    marketplace_count_orders = fields.Integer('Order Count', compute='_compute_count_of_records')
    marketplace_count_products = fields.Integer('Product Count', compute='_compute_count_of_records')
    marketplace_count_customers = fields.Integer('Customer Count', compute='_compute_count_of_records')
    marketplace_database_name = fields.Char('Database Name', compute='_compute_count_of_records')
    marketplace_current_user = fields.Char('Current User', compute='_compute_count_of_records')


    def _compute_count_of_records(self):
        """
        Count of Orders, Products, Customers for dashboard

        :return: None
        """
        for rec in self:
            search_query = [('marketplace_instance_id', '=', rec.id), ('shopify_id', '!=', False)]
            rec.marketplace_database_name = request.session.db
            rec.marketplace_current_user = self.env.user.id
            rec.marketplace_count_orders = rec.env['sale.order'].search_count(search_query)
            rec.marketplace_count_products = rec.env['shopify.product.mappings'].search_count([('shopify_instance_id', '=', rec.id)])
            rec.marketplace_count_customers = rec.env['res.partner'].search_count(search_query)

    def open_form_action(self):
        """
        Open the Operation Form View in the wizard

        :return: The form view
        """
        view = self.env.ref('syncoria_shopify.view_instance_form_shopify')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Operations',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'marketplace.instance',
            'view_mode': 'form',
            # 'context': {'default_marketplace_instances': [(4, 0, [self.id])], 'default_woo_instance': True},
            'target': 'new',
        }

    def shopify_open_marketplace_orders(self):
        """
        Open the view regarding the Sales Order with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.shopify_order_action').read()[0]
        action['domain'] = [('marketplace_instance_id', '=', self.id)]
        return action

    def shopify_open_marketplace_products(self):
        """
        Open the view regarding the Products with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.shopify_product_action').read()[0]
        action['domain'] = [('shopify_product_mapping_ids.shopify_instance_id','=', self.id)]
        return action


    def shopify_open_marketplace_customers(self):
        """
        Open the view regarding the Customers with respective to Instance

        :return: The view
        """
        action = self.env.ref('syncoria_shopify.res_partner_action_customer').read()[0]
        action['domain'] = [('marketplace_instance_id', '=', self.id)]
        return action

    def shopify_open_marketplace_configuration(self):
        """
        Open the Shopify Configuration wizard

        :return: The form view
        """
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Operations',
            'view': 'form',
            'res_id': self.id,
            'res_model': 'marketplace.instance',
            'view_mode': 'form',
        }

    def shopify_open_instance_logs(self):
        """
        Redirect to the Instance log form view

        :return: The tree view
        """
        action = self.env.ref('os_marketplace.action_marketplace_logging').read()[0]
        action['domain'] = [('marketplace_instance_id', '=', self.id)]
        return action


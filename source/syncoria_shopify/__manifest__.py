# -*- coding: utf-8 -*-

######################################################################################
#
#    Syncoria Inc.
#
#    Copyright (C) 2022-TODAY Syncoria Inc.(<https://www.syncoria.com>).
#    Author: Syncoria Inc.
#
#    This program is under the terms of the Odoo Proprietary License v1.0 (OPL-1)
#    It is forbidden to publish, distribute, sublicense, or sell copies of the Software
#    or modified copies of the Software.
#
#    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
#    IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
#    DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
#    ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#    DEALINGS IN THE SOFTWARE.
#
########################################################################################
{
    'name': "Odoo Shopify Connector",
    "version": "19.1.1",
    'summary': """Odoo Shopify Connector""",
    'description': """Odoo Shopify Connector""",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    'category': 'Sales',
    'version': '18.1.4',
    'depends': ['base','os_marketplace'],
    'images': [
        'static/description/banner.gif',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/shopify_products_wiz_views.xml',
        'data/feed_actions.xml',
        'data/ir_cron_data.xml',
        'data/shopify_err_tag_data.xml',
        'data/ir_sequence_data.xml',
        'data/product.xml',
        'data/res_partner.xml',
        'data/update_history.xml',
        'views/res_partner.xml',
        'views/res_config_settings.xml',
        'views/product_template.xml',
        'views/marketplace_instance.xml',
        'views/sale_order.xml',
        'views/stock.xml',
        'views/shopify_warehouse_views.xml',
        'views/shopify_fulfilment.xml',
        'wizard/fetch_product_wiz.xml',
        'wizard/fetch_warehouse_wiz_view.xml',
        'wizard/update_stock.xml',
        'views/feed_products.xml',
        'views/feed_orders.xml',
        'views/feed_customers.xml',
        'views/shopify_transactions.xml',
        'views/shopify_refunds.xml',
        'views/shopify_dashnoard_view.xml',
        # 'views/ir_cron.xml',
        'wizard/fetch_wiz_inherit.xml',
        'views/shopify_product_mappings_views.xml',
        'views/account_move_views.xml',
        'views/shopify_image_queue_views.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'syncoria_shopify/static/src/css/style.css',
        ],
    },

}

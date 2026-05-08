# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Delivery",
    "version": "19.1.1",
    'summary': """
        Dependency Module of Odoo Sync Base for delivery functionality""",
    'description': """
        It is the module for add delivery feature for Odoo Sync.
    """,
    # "category": "Customization",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    'depends': ['odoosync_base',"delivery","stock", "stock_delivery",],
    'data': [
        # Base Account 
        'views/omni_account_delivery.xml',

        # # =====================================================================================
        # # =============================Delivery:Purolator======================================
        # # =====================================================================================

        "delivery_apps/delivery_purolator/security/ir.model.access.csv",
        "delivery_apps/delivery_purolator/data/delivery_purolator.xml",
        "delivery_apps/delivery_purolator/views/delivery_purolator_view.xml",
        "delivery_apps/delivery_purolator/views/res_config_settings_views.xml",
        "delivery_apps/delivery_purolator/views/stock_picking_views.xml",
        "delivery_apps/delivery_purolator/views/choose_delivery_carrier.xml",
        "delivery_apps/delivery_purolator/views/product_template_views.xml",
        "delivery_apps/delivery_purolator/views/sale.xml",


        # # =====================================================================================
        # # =============================Delivery:Canadapost=====================================
        # # =====================================================================================
        'delivery_apps/delivery_canada_post/security/ir.model.access.csv',
        'delivery_apps/delivery_canada_post/data/delivery_canadapost.xml',
        'delivery_apps/delivery_canada_post/data/canapost_services.xml',
        'delivery_apps/delivery_canada_post/views/delivery_canada_post.xml',
        'delivery_apps/delivery_canada_post/views/choose_delivery_carrier.xml',
        'delivery_apps/delivery_canada_post/views/sale_order.xml',
        'delivery_apps/delivery_canada_post/views/res_company.xml',
        'delivery_apps/delivery_canada_post/views/product.xml',
        "delivery_apps/delivery_canada_post/views/stock_picking_views.xml",
        
    ],
}

# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Website Delivery ",
    "version": "19.1.1",
    "summary": """Dependency Module of Odoo Sync Delivery Website functionality""",
    "description": """It is the module for add website delivery feature for Odoo Sync.""",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    "category": "Customization",
    "depends": ["os_delivery", "website_sale","delivery"],
    "data": [
        # # =====================================================================================
        # # =============================Delivery:Purolator======================================
        # # =====================================================================================
        "delivery_apps/delivery_purolator/views/webclient_templates.xml",
        # # =====================================================================================
        # # =============================Delivery:Canadapost=====================================
        # # =====================================================================================
        "delivery_apps/delivery_canada_post/views/webclient_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            # Delivery
            "os_delivery_website/static/src/js/common_widget.js"
            # "os_delivery_website/delivery_apps/delivery_purolator/static/src/js/widget.js",
            # "os_delivery_website/delivery_apps/delivery_purolator/static/src/xml/website_sale_delivery_purolator_table.xml",
            # "os_delivery_website/delivery_apps/delivery_purolator/static/src/css/delivery_purolator.css",
            # "os_delivery_website/delivery_apps/delivery_canada_post/static/src/js/widget.js",
            # "os_delivery_website/delivery_apps/delivery_canada_post/static/src/css/delivery_canada_post.css",
        ],
    },
    'uninstall_hook': 'uninstall_hook',
}

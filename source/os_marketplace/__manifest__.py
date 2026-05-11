# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Marketplace",
    "version": "19.1.1",
    'summary': """
        Dependency Module of Odoo Sync Base for marketplace functionality""",
    'description': """
        It is the module for add marketplace feature for Odoo Sync.
    """,
    "category": "Customization",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    'depends': ['odoosync_base', 'stock',  'delivery',],
    'data': [
        "data/ir_sequence_data.xml",
        "security/ir.model.access.csv",
        "security/marketplace_security.xml",
        "views/instance_view.xml",
        "views/marketplace_logging.xml",
        "wizard/fetch_customers_wiz.xml",
        "wizard/fetch_orders_wiz.xml",
        "wizard/fetch_products_wiz.xml",
        "views/omni_account_marketplace.xml"
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

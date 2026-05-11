# -*- coding: utf-8 -*-
{
    "name": "Odoo Sync Base",
    "version": "19.1.1",
    "summary": "Odoo Sync Base",
    "description": """Odoo Sync Base""",
    "category": "Customization",
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    "depends": [
        "base",
        "mail",
        "sale_management",
        "account"
    ],
    'images': [
            'static/description/banner.gif',
        ],
    "data": [
        "security/omniaccount_security.xml",
        "security/ir.model.access.csv",
        "views/omni_account.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "pre_init_hook": "pre_init_check",
}

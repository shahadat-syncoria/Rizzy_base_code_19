# -*- coding: utf-8 -*-
{
    'name': "Odoo Sync Payment Pos",
    "version": "19.1.2",
    'summary': """
       Add pos feature to payment""",

    'description': """
        Add pos feature to payment
    """,

    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",

    'category': 'Payment',

    # any module necessary for this one to work correctly
    'depends': ['os_payment', 'point_of_sale'],

    # always loaded
    'data': [
        # OmniAccount Views
        'security/ir.model.access.csv',
        'data/force_done_card_names.xml',
        'views/pos_force_done_card_name_views.xml',
        'views/omni_account_payment.xml',
        'views/pos_payment_method_card_wise_journal.xml',

        # Moeris Cloud
        'payment_apps/payment_moneris_cloud/views/pos_payment_method_views.xml',
        'payment_apps/payment_moneris_cloud/views/pos_payment.xml',
        'payment_apps/payment_moneris_cloud/views/pos_config.xml',
        'payment_apps/payment_moneris_cloud/views/moneris_preauth_view.xml',

        # Clover Cloud
        'payment_apps/odoo_clover_cloud/views/custom_pos_view.xml',
        'payment_apps/odoo_clover_cloud/views/order_assets.xml',
        'payment_apps/odoo_clover_cloud/views/pos_order.xml',
        'payment_apps/odoo_clover_cloud/views/pos_payment_method_views.xml',
        'payment_apps/odoo_clover_cloud/views/pos_payment.xml',
        'payment_apps/odoo_clover_cloud/views/template.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [

            'os_payment_pos/static/lib/clover_cloud/clover_bundle.js',
            'os_payment_pos/static/src/js/clover_cloud/**/*',

            'os_payment_pos/static/lib/moneris_cloud/moneris_bundle.js',
            'os_payment_pos/static/src/js/moneris_cloud/**/*',
            'os_payment_pos/static/src/js/moneris_cloud/**/*.xml',
            'os_payment_pos/static/src/xml/moneris_cloud/**/*',

        ],
    },

    # 'assets': {
        # 'point_of_sale.assets': [
        #     'os_payment_pos/payment_apps/odoo_clover_cloud/static/lib/clover_cloud/clover.bundle.js',
        #     # 'os_payment_pos/payment_apps/odoo_clover_cloud/static/src/js/models.js',
        #     'os_payment_pos/payment_apps/odoo_clover_cloud/static/src/js/models/models.js',
        #     'os_payment_pos/payment_apps/odoo_clover_cloud/static/src/js/payment_clover_change.js',
        #     # 'os_payment_pos/payment_apps/odoo_clover_cloud/static/src/js/pos_models.js',
        #     # 'os_payment_pos/payment_apps/odoo_clover_cloud/static/src/js/TicketScreen.js',
        #
        #     # 'os_payment_pos/payment_apps/payment_moneris_cloud/static/lib/moneris_cloud/moneris.bundle.js',
        #     # 'os_payment_pos/payment_apps/payment_moneris_cloud/static/src/js/models.js',
        #     # 'os_payment_pos/payment_apps/payment_moneris_cloud/static/src/js/payment_moneris.js',
        #     # 'os_payment_pos/payment_apps/payment_moneris_cloud/static/src/js/pos_models.js',
        #     # 'os_payment_pos/payment_apps/payment_moneris_cloud/static/src/js/TicketScreen.js',
            # 'os_payment_pos/static/src/xml/**/*',
        # ],

        # 'web.assets_qweb': [
        #     'os_payment_pos/static/src/xml/**/*',
        # ],
    # },

}

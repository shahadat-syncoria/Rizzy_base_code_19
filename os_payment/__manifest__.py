# -*- coding: utf-8 -*-
{
    'name': "Odoo Sync Payment Apps",
    "version": "19.1.3",
    'summary': """Odoo Sync Payment Apps""",
    'description': """Odoo Sync Payment Apps""",
    'category': 'Payments',
    "author": "Syncoria Inc.",
    "website": "https://www.syncoria.com",
    "company": "Syncoria Inc.",
    "maintainer": "Syncoria Inc.",
    "license": "OPL-1",
    "support": "support@syncoria.com",
    "price": 5000,
    "currency": "USD",
    'depends': ['odoosync_base', 'account_payment','website_sale', 'payment'],
    'data': [
        'views/omni_account_payment.xml',
        # ======================================================================================
        # =============================Payment:Payment Gateway==================================
        # ======================================================================================
        # 1. Payment: Moneris Checkout
        'payment_apps/payment_moneris_checkout/security/moneris_groups.xml',
        'payment_apps/payment_moneris_checkout/security/ir.model.access.csv',
        'payment_apps/payment_moneris_checkout/data/payment_method.xml',
        'payment_apps/payment_moneris_checkout/data/payment_acquirer_data.xml',
        # 'payment_apps/payment_moneris_checkout/data/payment_provider_data.xml',
        'payment_apps/payment_moneris_checkout/views/payment_moneris_templates.xml',
        'payment_apps/payment_moneris_checkout/views/payment_views.xml',
        'payment_apps/payment_moneris_checkout/views/payment_token_views.xml',
        'payment_apps/payment_moneris_checkout/data/ir_cron_data.xml',

        # 2. Payment: Bambora Checkout
        # 'os_payment/payment_apps/odoo_bambora_checkout/security/ir.model.access.csv',
        'payment_apps/odoo_bambora_checkout/views/payment_bambora_templates.xml',
        'payment_apps/odoo_bambora_checkout/views/sale_order.xml',
        'payment_apps/odoo_bambora_checkout/views/payment_views.xml',
        'payment_apps/odoo_bambora_checkout/views/response_status.xml',
        'payment_apps/odoo_bambora_checkout/data/account_payment_methods.xml',

        # 3. Payment: Resolve Pay
        'payment_apps/resolve_pay/data/res_group.xml',
        'payment_apps/resolve_pay/security/ir.model.access.csv',
        'payment_apps/resolve_pay/views/resolvepay_view.xml',
        'payment_apps/resolve_pay/views/res_partner_view.xml',
        'payment_apps/resolve_pay/views/account_move_view.xml',
        'payment_apps/resolve_pay/views/fetch_wizard_view.xml',
        'payment_apps/resolve_pay/data/cron.xml',

       # 4. Payment: Clik2pay
        'payment_apps/payment_clik2pay/security/ir.model.access.csv',
        # 'payment_apps/payment_clik2pay/views/payment_provider_views.xml',
        'payment_apps/payment_clik2pay/views/payment_clik2pay_template.xml',
        'payment_apps/payment_clik2pay/views/clik2pay_webhook_log_views.xml',
        'payment_apps/payment_clik2pay/views/inherited_payment.xml',
        'payment_apps/payment_clik2pay/data/system_data.xml',
        'payment_apps/payment_clik2pay/data/account_payment_methods.xml',
        'payment_apps/payment_clik2pay/data/payment_icon_data.xml',
        'payment_apps/payment_clik2pay/data/refund_sync.xml',
        # 5. Payment: Rotessa
        'payment_apps/payment_rotessa/security/ir.model.access.csv',
        'payment_apps/payment_rotessa/views/res_partner.xml',
        'payment_apps/payment_rotessa/views/payment_provider_rotessa.xml',
        'payment_apps/payment_rotessa/views/res_partner_bank.xml',
        'payment_apps/payment_rotessa/views/rotessa_account_move.xml',
        'payment_apps/payment_rotessa/views/rotessa_transaction_tracking.xml',
        'payment_apps/payment_rotessa/data/account_payment_method.xml',
        'payment_apps/payment_rotessa/data/rotessa_sync.xml',
        # 'payment_apps/payment_rotessa/data/payment_provider.xml',
        # 6. Payment: GlobalPayment
        'payment_apps/payment_globalpay/views/payment_provider_views.xml',
        'payment_apps/payment_globalpay/views/payment_globalpay_template.xml',
        'payment_apps/payment_globalpay/data/payment_icon_data.xml',
        'payment_apps/payment_globalpay/data/account_payment_methods.xml',
        #
        # ======================================================================================
        # =============================POS Payment Methods======================================
        # ======================================================================================
        # 1. Clover Cloud Invoice Part
        'payment_apps/odoo_clover_cloud/security/ir.model.access.csv',
        'payment_apps/odoo_clover_cloud/views/clover_device.xml',
        'payment_apps/odoo_clover_cloud/views/account_journal.xml',
        # 'payment_apps/odoo_clover_cloud/views/account_move.xml',
        'payment_apps/odoo_clover_cloud/views/account_payment_register.xml',
        'payment_apps/odoo_clover_cloud/views/account_payment.xml',


        # 2. Moneris Cloud Invoice Part
        'payment_apps/payment_moneris_cloud/security/ir.model.access.csv',
        'payment_apps/payment_moneris_cloud/data/system_data.xml',
        'payment_apps/payment_moneris_cloud/views/moneris_device.xml',
        # 'payment_apps/payment_moneris_cloud/views/account_move.xml',
        'payment_apps/payment_moneris_cloud/views/account_journal.xml',
        'payment_apps/payment_moneris_cloud/views/account_payment.xml',
        'payment_apps/payment_moneris_cloud/views/account_payment_register.xml',
        'payment_apps/payment_moneris_cloud/wizard/sh_message_wizard.xml',

        'payment_apps/clover_checkout/views/payment_clover_checkout_template.xml',
        'payment_apps/clover_checkout/views/payment_provider_views.xml',
        'payment_apps/clover_checkout/data/payment_provider_data.xml',


    ],
    'assets':
        {
            'web.assets_frontend':
                [
                   "os_payment/static/src/js/payment_clik2pay/payment_form.js",
                    "os_payment/static/src/js/payment_globalpay/card.js",
                    "os_payment/static/src/js/payment_globalpay/payment_form.js",
                    "os_payment/static/src/js/payment_moneris_checkout/style.css",
                    "os_payment/static/src/js/payment_moneris_checkout/payment_form_inherit.js",
                    "os_payment/static/src/js/odoo_bambora_checkout/style.css",
                    "os_payment/static/src/js/odoo_bambora_checkout/payment_form.js",

                    # Clover checkout assets
                    'os_payment/static/src/js/payment_clover_checkout/style.css',
                    'os_payment/static/src/js/payment_clover_checkout/payment_form.js'
                ],
    },


    "installable": True,
    "application": False,
    "auto_install": False,
    # "pre_init_hook": "pre_init_check",
    # 'post_init_hook': 'post_init_hook',
    # 'uninstall_hook': 'uninstall_hook',
}

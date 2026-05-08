odoo.define('odoo_clover_cloud.pos_models.extend', function (require) {
    "use strict";
    
    var models = require('point_of_sale.models');
    models.load_models({
        model: "pos.order",
        domain: function (self) { return [['config_id', '=', self.config.id]]; },
        fields: ['name', 'session_id', 'date_order',  'pos_reference', 'partner_id', 'user_id', 'amount_total', 'pos_order_date', 
                 'clover_request_id', 'clover_ext_payment_ids','clover_last_action',
                'payment_ids',
                ],
        order:  _.map(['date_order'], function (name) { return {name: name, asc: false}; }),
        limit: 1,
        loaded: function (self, params) {
            self.clover_pos_orders = params;
        }

    }, {
        'after': "pos.config"
    });

});
    
odoo.define('odoo_clover_cloud.models', function (require) {

    var models = require('point_of_sale.models');
    var Paymentclover = require('odoo_clover_cloud.payment');

    models.register_payment_method('clover_cloud', Paymentclover);
    models.load_fields('pos.payment.method', [
        'clover_server_url',
        'clover_config_id',
        'clover_jwt_token',
        'clover_device_id',
        'clover_device_name',
        'clover_x_pos_id',
    ]);

    models.load_fields('pos.order', [
        'clover_request_id',
        'clover_ext_payment_ids',
        'clover_last_action',
    ]);

});

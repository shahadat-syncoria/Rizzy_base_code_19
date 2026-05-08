odoo.define('odoo_clover_cloud.models', function (require) {

    var models = require('point_of_sale.models');
    var Paymentclover = require('odoo_clover_cloud.payment');
    var { Order, Payment } = require('point_of_sale.models');
    const Registries = require('point_of_sale.Registries');

    models.register_payment_method('clover_cloud', Paymentclover);
    // models.load_fields('pos.payment.method', [
    //     'clover_server_url',
    //     'clover_config_id',
    //     'clover_jwt_token',
    //     'clover_device_id',
    //     'clover_device_name',
    //     'clover_x_pos_id',
    // ]);
    //
    // models.load_fields('pos.order', [
    //     'clover_request_id',
    //     'clover_ext_payment_ids',
    //     'clover_last_action',
    // ]);

    const PosCloverCloudPayment = (Payment) => class PosCloverPayment extends Payment {
    constructor(obj, options) {
        super(...arguments);
        this.clover_application_id = this.clover_application_id;
      this.clover_merchant_id = this.clover_merchant_id;
      this.clover_access_token = this.clover_access_token;
      this.clover_device_id = this.clover_device_id;
      this.clover_device_name = this.clover_device_name;
      this.clover_server = this.clover_server;
      this.clover_friendly_id = this.clover_friendly_id;
      this.clover_region = this.clover_region;
      this.clover_cloud_paired = this.clover_cloud_paired;
      this.clover_accept_signature = this.clover_accept_signature;
      // Other Fields
      this.clover_request_id = this.clover_request_id;
      this.clover_success = this.clover_success;
      this.clover_result = this.clover_result;
      this.clover_payment_id = this.clover_payment_id;
      this.clover_order_id = this.clover_order_id;
      this.clover_tender_id = this.clover_tender_id;
      this.clover_ext_id = this.clover_ext_id;
      this.clover_emp_id = this.clover_emp_id;
      this.clover_created_time = this.clover_created_time;
      this.clover_payment_result = this.clover_payment_result;

      this.clover_entry_type = this.clover_entry_type;
      this.clover_type = this.clover_type;
      this.clover_auth_code = this.clover_auth_code;
      this.clover_reference_id = this.clover_reference_id;
      this.clover_transaction_no = this.clover_transaction_no;
      this.clover_state = this.clover_state;
      this.clover_last_digits = this.clover_last_digits;
      this.clover_expiry_date = this.clover_expiry_date;
      this.clover_token = this.clover_token;
      // Odoo Basic Fields
      this.card_type = this.card_type;
      this.cardholder_name = this.cardholder_name;
      // Refunds
      this.clover_refund_reason = this.clover_refund_reason;
      this.clover_message = this.clover_message;
      this.clover_refund_id = this.clover_refund_id;
      this.clover_refund_device_id = this.clover_refund_device_id;
      this.clover_tax_amount = this.clover_tax_amount;
      this.clover_client_created_time = this.clover_client_created_time;
      this.clover_voided = this.clover_voided;
      this.clover_transaction_info = this.clover_transaction_info;

    }
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
       this.clover_application_id = json.clover_application_id;
      json.clover_merchant_id = this.clover_merchant_id;
      json.clover_access_token = this.clover_access_token;
      json.clover_device_id = this.clover_device_id;
      json.clover_device_name = this.clover_device_name;
      json.clover_server = this.clover_server;
      json.clover_friendly_id = this.clover_friendly_id;
      json.clover_region = this.clover_region;
      json.clover_cloud_paired = this.clover_cloud_paired;
      json.clover_accept_signature = this.clover_accept_signature;
      // Other Fields
      json.clover_request_id = this.clover_request_id;
      json.clover_success = this.clover_success;
      json.clover_result = this.clover_result;
      json.clover_payment_id = this.clover_payment_id;
      json.clover_order_id = this.clover_order_id;
      json.clover_tender_id = this.clover_tender_id;
      json.clover_ext_id = this.clover_ext_id;
      json.clover_emp_id = this.clover_emp_id;
      json.clover_created_time = this.clover_created_time;
      json.clover_payment_result = this.clover_payment_result;

      json.clover_entry_type = this.clover_entry_type;
      json.clover_type = this.clover_type;
      json.clover_auth_code = this.clover_auth_code;
      json.clover_reference_id = this.clover_reference_id;
      json.clover_transaction_no = this.clover_transaction_no;
      json.clover_state = this.clover_state;
      json.clover_last_digits = this.clover_last_digits;
      json.clover_expiry_date = this.clover_expiry_date;
      json.clover_token = this.clover_token;
      // Odoo Basic Fields
      json.card_type = this.card_type;
      json.cardholder_name = this.cardholder_name;
      // Refunds
      json.clover_refund_reason = this.clover_refund_reason;
      json.clover_message = this.clover_message;
      json.clover_refund_id = this.clover_refund_id;
      json.clover_refund_device_id = this.clover_refund_device_id;
      json.clover_tax_amount = this.clover_tax_amount;
      json.clover_client_created_time = this.clover_client_created_time;
      json.clover_voided = this.clover_voided;
      json.clover_transaction_info = this.clover_transaction_info;
        return json;
    }
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
       this.clover_application_id = json.clover_application_id;
      this.clover_merchant_id = json.clover_merchant_id;
      this.clover_access_token = json.clover_access_token;
      this.clover_device_id = json.clover_device_id;
      this.clover_device_name = json.clover_device_name;
      this.clover_server = json.clover_server;
      this.clover_friendly_id = json.clover_friendly_id;
      this.clover_region = json.clover_region;
      this.clover_cloud_paired = json.clover_cloud_paired;
      this.clover_accept_signature = json.clover_accept_signature;
      // Other Fields
      this.clover_request_id = json.clover_request_id;
      this.clover_success = json.clover_success;
      this.clover_result = json.clover_result;
      this.clover_payment_id = json.clover_payment_id;
      this.clover_order_id = json.clover_order_id;
      this.clover_tender_id = json.clover_tender_id;
      this.clover_ext_id = json.clover_ext_id;
      this.clover_emp_id = json.clover_emp_id;
      this.clover_created_time = json.clover_created_time;
      this.clover_payment_result = json.clover_payment_result;

      this.clover_entry_type = json.clover_entry_type;
      this.clover_type = json.clover_type;
      this.clover_auth_code = json.clover_auth_code;
      this.clover_reference_id = json.clover_reference_id;
      this.clover_transaction_no = json.clover_transaction_no;
      this.clover_state = json.clover_state;
      this.clover_last_digits = json.clover_last_digits;
      this.clover_expiry_date = json.clover_expiry_date;
      this.clover_token = json.clover_token;
      // Odoo Basic Fields
      this.card_type = json.card_type;
      this.cardholder_name = json.cardholder_name;
      // Refunds
      this.clover_refund_reason = json.clover_refund_reason;
      this.clover_message = json.clover_message;
      this.clover_refund_id = json.clover_refund_id;
      this.clover_refund_device_id = json.clover_refund_device_id;
      this.clover_tax_amount = json.clover_tax_amount;
      this.clover_client_created_time = json.clover_client_created_time;
      this.clover_voided = json.clover_voided;
      this.clover_transaction_info = json.clover_transaction_info;

    }
}
    Registries.Model.extend(Payment, PosCloverCloudPayment);


    const PosCloverCloudOrder = (Order) => class PosCloversOrder extends Order {
    constructor(obj, options) {
        super(...arguments);
        this.clover_request_id = this.clover_request_id;
        this.clover_ext_payment_ids = this.clover_ext_payment_ids;
        this.clover_last_action = this.clover_last_action;


    }
    //@override
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.clover_request_id = this.clover_request_id;
        json.clover_ext_payment_ids = this.clover_ext_payment_ids;
        json.clover_last_action = this.clover_last_action;


        return json;
    }
    //@override
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.clover_request_id = json.clover_request_id;
        this.clover_ext_payment_ids = json.clover_ext_payment_ids;
        this.clover_last_action = json.clover_last_action;

    }
}
    Registries.Model.extend(Order, PosCloverCloudOrder);

});

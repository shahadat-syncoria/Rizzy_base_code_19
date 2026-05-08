/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/store/pos_store";
import {Order, Payment } from "@point_of_sale/app/store/models";
import { PaymentAdyen } from "@os_payment_pos/payment_apps/odoo_clover_cloud/static/src/payment_clover_change";
import { patch } from "@web/core/utils/patch";
import {PaymentClover} from "../payment_clover_change";

register_payment_method("clover_cloud", PaymentClover);

patch(Payment.prototype, {
    setup(obj, options) {
        super.setup(...arguments);
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
});

patch(Order.prototype,{
    setup(obj, options) {
        super.setup(...arguments);
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
})
/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/services/pos_store";
import {PaymentClover} from "@os_payment_pos/js/clover_cloud/payment_clover_change";

register_payment_method("clover_cloud", PaymentClover);
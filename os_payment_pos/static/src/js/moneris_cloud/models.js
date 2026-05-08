/** @odoo-module */
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

import {PaymentMonerisCloud} from "@os_payment_pos/js/moneris_cloud/payment_moneris";

register_payment_method("moneris_cloud", PaymentMonerisCloud);

/** @odoo-module */

import {TicketScreen} from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import {patch} from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(TicketScreen.prototype, {

    async _get_clover_order_information(order_id) {

        let order_data = await rpc('/clovercloud/get_order_info', {
                "order_id": order_id,
            }
        );
        if (order_data) {
            var parsed_data = JSON.parse(order_data)
            var data = {
                "clover_request_id": parsed_data.clover_request_id,
                "clover_ext_payment_ids": parsed_data.clover_ext_payment_ids,
            }
            return data
        }
    },
    async onDoRefund() {
        const order = this.getSelectedOrder()


        let order_data = await this._get_clover_order_information(order.id);
        var clover_request_id, clover_ext_payment_ids, clover_last_action;

        if (order_data.clover_request_id){
            clover_request_id = order_data.clover_request_id;
            clover_last_action=false;
        }

        // var clover_request_id, clover_ext_payment_ids, clover_last_action;
        // cloverOrders.forEach(element => {
        //     if (element.pos_reference === order.name) {
        //         clover_request_id = element.clover_request_id;
        //         clover_ext_payment_ids = element.clover_ext_payment_ids;
        //         clover_last_action = element.clover_last_action;
        //     }
        // });

        // console.log("clover_request_id ===>>>", clover_request_id);
        // console.log("clover_ext_payment_ids ===>>>", clover_ext_payment_ids);
        // console.log("clover_last_action ===>>>", clover_last_action);




        const partner = order.getPartner();
        const destinationOrder =
                    this.props.destinationOrder &&
                    this.props.destinationOrder.lines.every(
                        (l) =>
                            l.quantity >= 0 || order.lines.some((ol) => ol.id === l.refunded_orderline_id)
                    ) &&
                    partner === this.props.destinationOrder.get_partner() &&
                    !this.pos.doNotAllowRefundAndSales()
                        ? this.props.destinationOrder
                        : this._getEmptyOrder(partner);
        if (destinationOrder) {
            destinationOrder.clover_request_id = clover_request_id;
            // destinationOrder.clover_ext_payment_ids = clover_ext_payment_ids;
            destinationOrder.clover_last_action = clover_last_action;

        }
        await super.onDoRefund(...arguments);
    }


});

/** @odoo-module */

import {TicketScreen} from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import {patch} from "@web/core/utils/patch";

patch(TicketScreen.prototype, {
    async _get_order_information(order_receipt_id) {

                let order_data = await rpc.query({
                    route: '/moneriscloud/get_order_info',
                    params: {
                        "order_receipt_id": order_receipt_id,
                    },
                })
                if (order_data) {
                    var parsed_data=JSON.parse(order_data)
                    var data = {
                    "moneris_cloud_receiptid" : parsed_data.moneris_cloud_receiptid,
                    "moneris_cloud_transid" : parsed_data.moneris_cloud_transid,
                    }
                    return data
                }
            },
    async onDoRefund() {
                console.log("====================>onDoRefund");

                const order = this.getSelectedOrder();
                // this.env.pos.moneris_pos_orders.push(order);
                const monerisOrders = this.pos.moneris_pos_orders;

                console.log("order ===>>>", order);
                console.log("monerisOrders ===>>>", monerisOrders);
                var moneris_cloud_cloudticket,  moneris_cloud_receiptid, moneris_cloud_transid,last_order_ref;
               debugger
                monerisOrders.forEach(element => {
                    if(element.pos_reference === order.name){
                        moneris_cloud_cloudticket = element.moneris_cloud_cloudticket;
                        moneris_cloud_receiptid = element.moneris_cloud_receiptid;
                        moneris_cloud_transid = element.moneris_cloud_transid;
                        last_order_ref = element.pos_reference;
                    }
                });

               if (last_order_ref === undefined){
                   let order_data = await this._get_order_information(order.name);
                   if (order_data){
                        moneris_cloud_receiptid = order_data.moneris_cloud_receiptid;
                        moneris_cloud_transid = order_data.moneris_cloud_transid;
                        last_order_ref = order.name;
                   }
               }

                console.log("moneris_cloud_cloudticket ===>>>", moneris_cloud_cloudticket);
                console.log("moneris_cloud_receiptid ===>>>", moneris_cloud_receiptid);
                console.log("moneris_cloud_transid ===>>>", moneris_cloud_transid);
                console.log("moneris_cloud_transid ===>>>", last_order_ref);


                super.onDoRefund(...arguments);

                const partner = order.get_partner();
                const destinationOrder = this.props.destinationOrder &&
                    partner === this.props.destinationOrder.get_partner() &&
                    !this.pos.doNotAllowRefundAndSales()
                        ? this.props.destinationOrder
                        : this._getEmptyOrder(partner);
                if(destinationOrder && moneris_cloud_transid){
                    destinationOrder.moneris_cloud_cloudticket = moneris_cloud_cloudticket;
                    destinationOrder.moneris_cloud_receiptid = moneris_cloud_receiptid;
                    destinationOrder.moneris_cloud_transid = moneris_cloud_transid;
                    destinationOrder.last_order_ref = last_order_ref;

                }

                if (last_order_ref != undefined || last_order_ref != null) {

                    this.env.pos.moneris_cloud_cloudticket = moneris_cloud_cloudticket;
                    this.env.pos.moneris_cloud_receiptid = moneris_cloud_receiptid;
                    this.env.pos.moneris_cloud_transid = moneris_cloud_transid;
                    this.env.pos.last_order_ref = last_order_ref;
                }

                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_cloudticket);
                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_receiptid);
                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_transid);

            }
});
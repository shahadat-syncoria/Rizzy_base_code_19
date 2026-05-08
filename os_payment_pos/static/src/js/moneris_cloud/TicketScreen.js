/** @odoo-module */

import {TicketScreen} from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import {patch} from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";

patch(TicketScreen.prototype, {
    async _get_order_information(order_receipt_id) {

                let order_data = await rpc('/moneriscloud/get_order_info',{
                        "order_receipt_id": order_receipt_id,
                    }
                );
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

                console.log("order ===>>>", order);
                var moneris_cloud_cloudticket,  moneris_cloud_receiptid, moneris_cloud_transid,last_order_ref;

               if (last_order_ref === undefined){
                   let order_data = await this._get_order_information(order.pos_reference);
                   if (order_data){
                        moneris_cloud_receiptid = order_data.moneris_cloud_receiptid;
                        moneris_cloud_transid = order_data.moneris_cloud_transid;
                        last_order_ref = order.pos_reference;
                   }
               }

                console.log("moneris_cloud_cloudticket ===>>>", moneris_cloud_cloudticket);
                console.log("moneris_cloud_receiptid ===>>>", moneris_cloud_receiptid);
                console.log("moneris_cloud_transid ===>>>", moneris_cloud_transid);
                console.log("moneris_cloud_transid ===>>>", last_order_ref);




                const partner = order.getPartner();
                const destinationOrder =
                    this.props.destinationOrder &&
                    this.props.destinationOrder.lines.every(
                        (l) =>
                            l.quantity >= 0 || order.lines.some((ol) => ol.id === l.refunded_orderline_id)
                    ) &&
                    partner === this.props.destinationOrder.getPartner() &&
                    !this.pos.doNotAllowRefundAndSales()
                        ? this.props.destinationOrder
                        : this._getEmptyOrder(partner);
                if(destinationOrder && moneris_cloud_transid){
                    destinationOrder.moneris_cloud_cloudticket = moneris_cloud_cloudticket;
                    destinationOrder.moneris_cloud_receiptid = moneris_cloud_receiptid;
                    destinationOrder.moneris_cloud_transid = moneris_cloud_transid;
                    destinationOrder.last_order_ref = last_order_ref;

                }

                if ((last_order_ref != undefined || last_order_ref != null) && moneris_cloud_transid !== false) {

                    this.pos.moneris_cloud_cloudticket = moneris_cloud_cloudticket;
                    this.pos.moneris_cloud_receiptid = moneris_cloud_receiptid;
                    this.pos.moneris_cloud_transid = moneris_cloud_transid;
                    this.pos.last_order_ref = last_order_ref;
                }

                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_cloudticket);
                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_receiptid);
                console.log("moneris_cloud_cloudticket ===>>>", destinationOrder.moneris_cloud_transid);

                await super.onDoRefund(...arguments);
            }
});
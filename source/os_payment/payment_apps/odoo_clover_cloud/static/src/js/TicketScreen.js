odoo.define('odoo_clover_cloud.TicketScreen', function (require) {
    'use strict';

    const TicketScreen = require('point_of_sale.TicketScreen');
    const Registries = require('point_of_sale.Registries');


    const CloverPosTicketScreen = (TicketScreen) =>
        class extends TicketScreen {
            async _onDoRefund() {
                console.log("_onDoRefund");
                const order = this.getSelectedSyncedOrder();
                const cloverOrders = this.env.pos.clover_pos_orders;

                console.log("order ===>>>", order);
                console.log("cloverOrders ===>>>", cloverOrders);
                var clover_request_id,  clover_ext_payment_ids, clover_last_action;
                cloverOrders.forEach(element => {
                    if(element.pos_reference === order.name){
                        clover_request_id = element.clover_request_id;
                        clover_ext_payment_ids = element.clover_ext_payment_ids;
                        clover_last_action = element.clover_last_action;
                    }
                });

                console.log("clover_request_id ===>>>", clover_request_id);
                console.log("clover_ext_payment_ids ===>>>", clover_ext_payment_ids);
                console.log("clover_last_action ===>>>", clover_last_action);


                super._onDoRefund();

                const destinationOrder = this.env.pos.get_order();
                if(destinationOrder){
                    destinationOrder.clover_request_id = clover_request_id;
                    destinationOrder.clover_ext_payment_ids = clover_ext_payment_ids;
                    destinationOrder.clover_last_action = clover_last_action;

                }

                console.log("clover_request_id ===>>>", destinationOrder.clover_request_id);
                console.log("clover_ext_payment_ids ===>>>", destinationOrder.clover_ext_payment_ids);
                console.log("clover_last_action ===>>>", destinationOrder.clover_last_action);

            }
        };

    Registries.Component.extend(TicketScreen, CloverPosTicketScreen);

    
});

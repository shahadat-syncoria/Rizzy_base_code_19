/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class SelectPreauthPopup extends Component {
    static template = "os_payment_pos.SelectPreauthPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        customerId: Number,
        monerisPaymentMethodId: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.pos = usePos();
        this.notification = useService("notification");
        this.ui = useState(useService("ui"));

        this.state = useState({
            preauthOrders: [],
            selectedOrder: null,
            loading: true,
        });

        onWillStart(async () => {
            await this.loadPreauthOrders();
        });
    }

    async loadPreauthOrders() {
        try {
            const orders = await this.orm.searchRead(
                "moneris.pos.preauth",
                [
                    ["customer_id", "=", this.props.customerId],
                    ["status", "=", "confirmed"],
                    ["moneris_go_payment_method",'in',this.props.monerisPaymentMethodId.map(m => m.id)]
                ],
                ["name", "order_date", "order_id", "transaction_id",'moneris_go_payment_method', "total_amount", "status"]
            );
            this.state.preauthOrders = orders;
        } catch (err) {
            console.error(err);
            this.notification.add("Failed to load preauth orders", {type: "danger"});
        } finally {
            this.state.loading = false;
        }
    }

    selectOrder(order) {
        this.state.selectedOrder = order;
    }

    async confirmSelection() {
        if (!this.state.selectedOrder) {
            this.notification.add("Please select a preauth order.", {type: "warning"});
            return;
        }


        const order = this.pos.getOrder();
        if (order.remainingDue < this.state.selectedOrder.total_amount) {
            this.notification.add("Authorized amount is greater than remaining amount.", {type: "warning"});
            return;
        }
        const matchedMethod = this.props.monerisPaymentMethodId.find(
        pm => pm.id === this.state.selectedOrder.moneris_go_payment_method[0]
        );

        if (!matchedMethod) {
            this.notification.add("No matching Moneris payment method found.", { type: "danger" });
            return;
        }
        try {
            this.state.loading = true;
            const args = [this.state.selectedOrder,matchedMethod.id,order.id, ...(this.props.extraArgs || [])];
            const res = await this.orm.call(
                "moneris.pos.preauth",
                "moneris_preauth_complete_req",
                args,
                {}
            );

            console.log("RPC OK:", res);
            const response = JSON.parse(res);
            if (response.errors_message) {
                return this.notification.add("Moneris GO Error: " + (response.errors_message), {
                    type: "danger",
                    sticky: true
                });
            }
            else if (response.error) {
                return this.notification.add("Moneris GO Error: " + (response.description), {
                    type: "danger",
                    sticky: true
                });
            }
            else{
                order.addPaymentline(matchedMethod);
                order.getSelectedPaymentline().setAmount(this.state.selectedOrder.total_amount);
                order.getSelectedPaymentline().setPaymentStatus('done');
            }


            this.props.close();
        } catch (e) {
            console.error("RPC ERROR:", e);
            this.notification.add("Operation failed: " + (e?.message || e), {type: "danger"});
        } finally {
            this.state.loading = false;
        }


    }
}

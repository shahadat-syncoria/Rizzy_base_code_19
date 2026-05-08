import {PaymentScreen} from "@point_of_sale/app/screens/payment_screen/payment_screen";
import {patch} from "@web/core/utils/patch";
import {SelectPreauthPopup} from "./popup/select_preauth_popup";

patch(PaymentScreen.prototype, {
        async onClickSelectPreauthView(event) {
            const order = this.currentOrder;
            const customer = order.getPartner();
            if (!customer) {
                this.env.services.notification.add("Please select a customer before selecting a preauth.", {type: "warning"});
                return;
            }
            const allMethods = this.pos.config.payment_method_ids; // POS model cache
            const is_moneris_go = allMethods.filter(pm => pm.is_moneris_go_cloud);
            if (!is_moneris_go) {
                this.env.services.notification.add("Moneris Go is not available as payment method! Please add Syncoria Moneris Go Payment Method.", {type: "warning"});
                return;
            }
            debugger
            this.dialog.add(SelectPreauthPopup, {
                customerId: customer.id,
                monerisPaymentMethodId:is_moneris_go
            });
        }
    }
)

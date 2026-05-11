/** @odoo-module **/

import {ControlButtons} from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import {patch} from "@web/core/utils/patch";
import {MonerisGoPreauthPopup} from "../popup/preauth_popup";



patch(ControlButtons.prototype, {

      async onClickPreauthView(event) {
        this.dialog.add(MonerisGoPreauthPopup, {
            title: 'Moneris Go Preauth List',
            cancel: () => true,
        });
    }
});
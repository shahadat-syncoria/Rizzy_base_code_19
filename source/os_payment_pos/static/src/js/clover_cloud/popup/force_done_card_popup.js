import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class CloverForceDoneCardPopup extends Component {
    static template = "os_payment_pos.CloverForceDoneCardPopup";
    static components = { Dialog };

    static props = {
        title: { type: String },
        amount: Number,
        cardOptions: { type: Array },
        confirm: { type: Function },
        close: { type: Function },
    };

    setup() {
        super.setup(...arguments);
        this.state = useState({
            card: (this.props.cardOptions[0] && this.props.cardOptions[0].value) || "",
        });
        this.formattedAmount = Number(this.props.amount || 0).toFixed(2);
    }

    onConfirm() {
        this.props.confirm({ card: this.state.card });
        this.props.close();
    }

    onCancel() {
        this.props.close();
    }
}


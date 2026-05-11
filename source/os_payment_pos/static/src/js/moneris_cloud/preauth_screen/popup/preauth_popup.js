/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class MonerisGoPreauthPopup extends Component {
    static template = "os_payment_pos.MonerisGoPreauthPopup";
    static components = { Dialog };

    // Provide model & method to call. Optional: title, domain, fields, limit, extraArgs
    static props = {
        cancel: Function,
        close: Function,
        title: { type: String, optional: true },
        domain: { type: Array, optional: true },    // custom partner domain
        fields: { type: Array, optional: true },    // extra partner fields to read
        limit: { type: Number, optional: true },    // max partners to fetch
        extraArgs: { type: Array, optional: true }, // extra args appended to RPC
    };

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.ui = useState(useService("ui"));
        this.orm = useService("orm");
        this.state = useState({
            title: this.props.title || "Customer & Amount",
            customers: [],
            customerId: null,
            paymentMethods: [],
            paymentMethodId: null,
            amount: "",
            loading: true,
        });
        this.loadCustomers();
        this.loadPaymentMethods();
    }

    async loadCustomers() {
        debugger
        try {
            // Defaults: only customers, read id+name, limit 100, ordered by name
            const domain = [];
            const fields =  ["name"];
            const limit =  100;

            const customers = await this.pos.data.call("res.partner", "search_read", [
                domain,
                ["id", ...fields],
                0,                // offset
                limit,            // limit
                "name",           // order
            ]);

            this.state.customers = customers || [];
            if (this.state.customers.length && !this.state.customerId) {
                this.state.customerId = this.state.customers[0].id;
            }
        } catch (err) {
            console.error("Failed to load customers:", err);
            this.notification.add("Could not fetch customer list.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }


    loadPaymentMethods() {
        // Filter Moneris Go Cloud payment methods
        const allMethods = this.pos.config.payment_method_ids; // POS model cache
        this.state.monerisMethods = allMethods.filter(pm => pm.is_moneris_go_cloud);

        // Auto-select if only one method
        if (this.state.monerisMethods.length === 1) {
            this.state.paymentMethodId = this.state.monerisMethods[0].id;
        }
    }

    get filteredCustomers() {
        if (!this.state.filterText) return this.state.customers;
        const q = this.state.filterText.toLowerCase();
        return this.state.customers.filter(c => c.name && c.name.toLowerCase().includes(q));
    }

    selectCustomer(id) {
        this.state.customerId = id;
        this.state.open = false;
    }

    async editPartner(p = false) {
        const partner = await this.pos.editPartner(p);
        if (partner) {
            this.clickPartner(partner);
        }
    }
    clickPartner(partner) {
        this.loadCustomers();
        this.state.customerId = partner.id
        // this.props.close();
    }

    async confirm() {
    debugger;
    const partnerId = this.state.customerId;
    const paymentMethodId = this.state.paymentMethodId;
    const amount = Number(this.state.amount);

    if (!partnerId) {
        this.notification.add("Please select a customer.", { type: "warning" });
        return;
    }
    if (!paymentMethodId) {
        this.notification.add("Please select a Moneris Go Payment Method.", { type: "warning" });
        return;
    }
    if (!amount || isNaN(amount) || amount <= 0) {
        this.notification.add("Please enter a valid amount.", { type: "warning" });
        return;
    }

    try {
        this.state.loading = true; // Start loader

        const args = [partnerId, amount, paymentMethodId, ...(this.props.extraArgs || [])];
        const res = await this.orm.call(
            "moneris.pos.preauth",          // model
            "moneris_preauth_req",          // method
            args,                           // args
            {}                              // kwargs
        );

        console.log("RPC OK:", res);
        const response = JSON.parse(res);

        if (response.errors_message) {
            return this.notification.add("Moneris GO Error: " + (response.errors_message), { type: "danger", sticky: true });
        }
        if (response.error){
            return this.notification.add("Moneris GO Error: " + (response.description), { type: "danger", sticky: true });
        }


        this.props.close();
    } catch (e) {
        console.error("RPC ERROR:", e);
        this.notification.add("Operation failed: " + (e?.message || e), { type: "danger" });
    } finally {
        this.state.loading = false; // Stop loader
    }
}
}

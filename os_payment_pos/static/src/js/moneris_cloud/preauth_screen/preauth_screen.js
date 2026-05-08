/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState } from "@odoo/owl";
import { SearchBar } from "@point_of_sale/app/screens/ticket_screen/search_bar/search_bar";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { CenteredIcon } from "@point_of_sale/app/components/centered_icon/centered_icon";
import { BackButton } from "@point_of_sale/app/screens/product_screen/action_pad/back_button/back_button";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";


const NBR_BY_PAGE = 30;

export class PreauthScreen extends Component {
    static template = "os_payment_pos.PreauthScreen";
    static components = { SearchBar, CenteredIcon, BackButton };

    setup() {
        this.orm = useService("orm");
        this.pos = usePos();
        this.ui = useState(useService("ui"));
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.state = useState({
            page: 1,
            totalCount: 0,
            preauthOrders: [],
            search: { searchTerm: "", fieldName: "NAME" },
            filter: null, // null = All
            loading: false,
        });

        // memoized search config (prevents re-trigger loops)
        this.searchConfig = {
            searchFields: new Map([
                ["NAME", _t("Name")],
                ["ORDER_ID", _t("Order ID")],
                ["TRANSACTION_ID", _t("Transaction ID")],
            ]),
            filter: {
                show: true,
                options: this._getStatusOptions(),
            },
            defaultSearchDetails: this.state.search,
            defaultFilter: this.state.filter,
        };

        onWillStart(async () => {
            await this.loadPreauthOrders();
        });
    }

    _getStatusOptions() {
        const states = new Map();
        states.set(null, { text: _t("All") });
        states.set("pending", { text: _t("Pending") });
        states.set("confirmed", { text: _t("Confirmed") });
        states.set("failed", { text: _t("Failed") });
        states.set("voided", { text: _t("Void") });
        states.set("settled", { text: _t("Settled") });
        return states;
    }

    getSearchBarConfig() {
        return this.searchConfig;
    }

    async onSearch(search) {
        this.state.search = search;
        this.state.page = 1;
        await this.loadPreauthOrders();
    }

    async onFilterSelected(selectedFilter) {
        this.state.filter = selectedFilter || null;
        this.state.page = 1;
        await this.loadPreauthOrders();
    }

    async loadPreauthOrders() {
        this.state.loading = true;
        try {
            const offset = (this.state.page - 1) * NBR_BY_PAGE;
            const domain = [];

            if (this.state.search.searchTerm) {
                const fieldMap = {
                    NAME: "name",
                    ORDER_ID: "order_id",
                    TRANSACTION_ID: "transaction_id",
                };
                domain.push([
                    fieldMap[this.state.search.fieldName],
                    "ilike",
                    this.state.search.searchTerm,
                ]);
            }

            if (this.state.filter) {
                domain.push(["status", "=", this.state.filter]);
            }

            const fields = [
                "name",
                "order_date",
                "order_id",
                "terminal_id",
                "total_amount",
                "transaction_id",
                "status",
                "customer_id",
                "moneris_go_payment_method",
            ];

            const [orders, count] = await Promise.all([
                this.orm.searchRead("moneris.pos.preauth", domain, fields, {
                    offset,
                    limit: NBR_BY_PAGE,
                    order: "order_date desc",
                }),
                this.orm.searchCount("moneris.pos.preauth", domain),
            ]);

            // ✅ update state once
            Object.assign(this.state, {
                preauthOrders: orders,
                totalCount: count,
            });
        } finally {
            this.state.loading = false;
        }
    }

    async nextPage() {
        if (this.state.page * NBR_BY_PAGE < this.state.totalCount) {
            this.state.page++;
            await this.loadPreauthOrders();
        }
    }

    async prevPage() {
        if (this.state.page > 1) {
            this.state.page--;
            await this.loadPreauthOrders();
        }
    }

    getPageNumber() {
        if (!this.state.totalCount) {
            return `1/1`;
        }
        return `${this.state.page}/${Math.ceil(
            this.state.totalCount / NBR_BY_PAGE
        )}`;
    }

    getDate(order) {
        return formatDateTime(deserializeDateTime(order.order_date));
    }

    getTotal(order) {
        return this.env.utils.formatCurrency(order.total_amount);
    }

    getPartner(order) {
        return order.customer_id ? order.customer_id[1] : "";
    }

    getStatusText(order) {
        const map = {
            pending: _t("Pending"),
            confirmed: _t("Confirmed"),
            failed: _t("Failed"),
            voided: _t("Voided"),
            settled: _t("Settled"),
        };
        return map[order.status] || order.status;
    }

    backCloseScreen() {
        return this.pos.navigate("ProductScreen");
    }

    confirmDeleteOrder(order) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Preauth Orders?"),
            body: _t("Are you sure? It will void the Moneris Go transaction."),
            confirmLabel: _t("Void Transaction"),
            cancelLabel: _t("Cancel"),
            confirm: async () => {
                try {
                    this.state.loading = true;
                    const res = await this.orm.call(
                        "moneris.pos.preauth",
                        "moneris_preauth_void_req",
                        [order],
                        {}
                    );
                    const response = JSON.parse(res);
                    if (response.error) {
                        this.notification.add(
                            "Moneris GO Error: " + (response.description || "Unknown Error"),
                            { type: "danger", sticky: true }
                        );
                    }
                } catch (e) {
                    console.error("RPC ERROR:", e);
                    this.notification.add(
                        "Operation failed: " + (e?.message || e),
                        { type: "danger" }
                    );
                } finally {
                    this.state.loading = false;
                }
                await this.loadPreauthOrders();
            },
        });
    }
}

// registry.category("pos_screens").add("PreauthScreen", PreauthScreen);
registry.category("pos_pages").add("PreauthScreen", {
    name: "PreauthScreen",
    component: PreauthScreen,
    route: `/pos/ui/${odoo.pos_config_id}/preauth`,
    params: {},
});

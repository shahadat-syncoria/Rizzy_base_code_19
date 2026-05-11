import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { CloverForceDoneCardPopup } from "@os_payment_pos/js/clover_cloud/popup/force_done_card_popup";

patch(PaymentScreen.prototype, {
    _getForceDoneTerminalKey(line) {
        const terminal = String(line?.payment_method_id?.use_payment_terminal || "").trim().toLowerCase();
        if (terminal === "clover_cloud") {
            return "clover_cloud";
        }
        if (terminal === "moneris_cloud") {
            return line?.payment_method_id?.is_moneris_go_cloud ? "moneris_cloud_go" : "moneris_cloud";
        }
        return "";
    },

    _getForceDoneCardOptions(line) {
        const rawCardIds = line?.payment_method_id?.force_done_card_name_ids || [];
        const terminalKey = this._getForceDoneTerminalKey(line);
        const cardIds = rawCardIds
            .map((item) => (typeof item === "number" ? item : item?.id))
            .filter((id) => Number.isInteger(id));
        const allCards = this.pos.models?.["pos.force.done.card.name"] || [];
        const cardsById = new Map(allCards.map((card) => [card.id, card]));
        let selectedCards = cardIds
            .map((id) => cardsById.get(id))
            .filter((card) => card?.name && card?.code);
        if (!selectedCards.length) {
            selectedCards = allCards
                .filter((card) => card?.name && card?.code && card?.terminal === terminalKey);
        }
        return selectedCards
            .sort((a, b) => (a.sequence || 0) - (b.sequence || 0))
            .map((card) => ({
                label: String(card.name).trim(),
                value: String(card.code).trim().toUpperCase(),
            }));
    },

    async sendForceDone(line) {
        const terminalKey = this._getForceDoneTerminalKey(line);
        if (!["clover_cloud", "moneris_cloud", "moneris_cloud_go"].includes(terminalKey)) {
            return super.sendForceDone(...arguments);
        }

        const previousStatus = line.payment_status;
        const cardOptions = this._getForceDoneCardOptions(line);
        if (!cardOptions.length) {
            this.dialog.add(AlertDialog, {
                title: _t("Force Done"),
                body: _t("No card names configured for this payment method."),
            });
            line.setPaymentStatus(previousStatus);
            return;
        }
        const selectedCard = await new Promise((resolve) => {
            this.dialog.add(CloverForceDoneCardPopup, {
                title: _t("Force Done"),
                amount: line.getAmount(),
                cardOptions,
                confirm: ({ card }) => resolve(card),
                close: () => resolve(false),
            });
        });

        if (!selectedCard) {
            line.setPaymentStatus(previousStatus);
            return;
        }

        line.card_name = selectedCard;
        line.card_type = selectedCard;
        line.clover_card_type = selectedCard;
        return super.sendForceDone(...arguments);
    },
});

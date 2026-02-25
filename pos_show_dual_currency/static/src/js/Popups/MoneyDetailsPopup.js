/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/utils/close_pos_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(ClosePosPopup.prototype, {
    
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.orm = useService("orm");

        this.manualInputCashCountUSD = false;
        Object.assign(this, this.props.info);

        this.state = useState({
            ...this.props.info.state,
            displayMoneyDetailsPopupUSD: false,
        });
    }

    async confirm() {
        if (!this.cashControl || !this.hasDifferenceUSD()) {
            return super.confirm();
        } else if (this.hasUserAuthorityUSD()) {
            const { confirmed } = await this.pos.showPopup("ConfirmPopup", {
                title: this.env._t("Currency Ref Payments Difference"),
                body: this.env._t(
                    "Do you want to accept currency ref payments difference and post a profit/loss journal entry?"
                ),
            });
            if (confirmed) return super.confirm();
        } else {
            await this.pos.showPopup("ConfirmPopup", {
                title: this.env._t("Currency Ref Payments Difference"),
                body: this.env._t(
                    "The maximum difference by currency ref allowed is %s.\nPlease contact your manager to accept the closing difference.",
                    this.pos.format_currency_ref(this.amountAuthorizedDiffUSD)
                ),
                confirmText: this.env._t("OK"),
            });
        }
    }

    openDetailsPopupUSD() {
        const refId = this.defaultCashDetails?.default_cash_details_ref?.id;
        if (!refId) return;

        this.state.payments_usd[refId].counted = 0;
        this.state.payments_usd[refId].difference = -this.defaultCashDetails.default_cash_details_ref.amount;
        this.state.displayMoneyDetailsPopupUSD = true;
    }

    closeDetailsPopupUSD() {
        this.state.displayMoneyDetailsPopupUSD = false;
    }

    handleInputChangeUSD(paymentId) {
        let expectedAmount;
        if (paymentId === this.defaultCashDetails.default_cash_details_ref.id) {
            this.manualInputCashCountUSD = true;
            expectedAmount = this.defaultCashDetails.default_cash_details_ref.amount;
        } else {
            expectedAmount = this.otherPaymentMethods.find((pm) => paymentId === pm.id).amount;
        }
        this.state.payments_usd[paymentId].difference = this.pos.round_decimals_currency(
            this.state.payments_usd[paymentId].counted - expectedAmount
        );
    }

    updateCountedCashUSD({ total_ref, moneyDetailsNotesRef }) {
        const refId = this.defaultCashDetails.default_cash_details_ref.id;

        this.state.payments_usd[refId].counted = total_ref;
        this.state.payments_usd[refId].difference = this.pos.round_decimals_currency(
            this.state.payments_usd[refId].counted - this.defaultCashDetails.default_cash_details_ref.amount
        );

        if (moneyDetailsNotesRef) {
            this.state.notes = (this.state.notes || "") + moneyDetailsNotesRef;
        }
        this.manualInputCashCountUSD = false;
        this.closeDetailsPopupUSD();
    }

    hasDifferenceUSD() {
        return Object.values(this.state.payments_usd || {}).some((pm) => pm.difference != 0);
    }

    hasUserAuthorityUSD() {
        const diffs = Object.values(this.state.payments_usd || {}).map((pm) => Math.abs(pm.difference || 0));
        const maxDiff = diffs.length ? Math.max(...diffs) : 0;
        return this.isManager || this.amountAuthorizedDiffUSD == null || maxDiff <= this.amountAuthorizedDiffUSD;
    }

    async closeSession() {
        if (this.closeSessionClicked) return;
        this.closeSessionClicked = true;

        try {
            if (this.cashControl) {
                const refId = this.defaultCashDetails.default_cash_details_ref.id;
                const counted = this.state.payments_usd[refId].counted;

                const response = await this.orm.call("pos.session", "post_closing_cash_details_ref", [
                    [this.pos.pos_session.id],
                    counted,
                ]);

                if (response && response.successful === false) {
                    this.closeSessionClicked = false;
                    return super.handleClosingError(response);
                }
            }

            await this.orm.call("pos.session", "update_closing_control_state_session_ref", [
                [this.pos.pos_session.id],
                this.state.notes || "",
            ]);
        } finally {
            this.closeSessionClicked = false;
        }

        return super.closeSession();
    }
}
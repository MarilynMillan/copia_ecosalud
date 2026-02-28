/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ClosePosPopup.prototype, {
    
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");

        // Merge state from both logic branches
        this.state = useState({
            ...this.state,
            openingCashUSD: this.pos.pos_session.cash_register_balance_start_mn_ref || 0,
            displayMoneyDetailsPopupUSD: false,
            // Payments state initialized in base getClosePosInfo? No, we need it here if we want to track differences.
            payments_usd: this.props.info?.state?.payments_usd || {},
        });

        this.manualInputCashCountUSD = false;
        if (this.props.info) {
             Object.assign(this, this.props.info);
        }
    },

    async confirm() {
        // Logic from MoneyDetailsPopup.js (Closing control validation)
        if (this.cashControl && this.hasDifferenceUSD()) {
             if (this.hasUserAuthorityUSD()) {
                const { confirmed } = await this.popup.add("ConfirmPopup", {
                    title: _t("Currency Ref Payments Difference"),
                    body: _t(
                        "Do you want to accept currency ref payments difference and post a profit/loss journal entry?"
                    ),
                });
                if (!confirmed) return;
            } else {
                await this.popup.add("ConfirmPopup", {
                    title: _t("Currency Ref Payments Difference"),
                    body: _t(
                        "The maximum difference by currency ref allowed is %s.\nPlease contact your manager to accept the closing difference.",
                        this.pos.format_currency_ref(this.amountAuthorizedDiffUSD)
                    ),
                    confirmText: _t("OK"),
                });
                return;
            }
        }

        // Logic from ClosePosPopup.js (Set cashbox USD)
        // Only if opening cash is modified? Or always?
        // This seems to be setting STARTING balance? "set_cashbox_pos_usd" usually implies opening.
        // But ClosePosPopup is closing.
        // If this module allows editing opening balance at closing (unlikely), then keeping it is fine.
        // But typically set_cashbox_pos is for Opening Control.
        // However, if we look at `CashOpeningPopup.js`, it calls `set_cashbox_pos_usd`.
        // Maybe `ClosePosPopup` here shouldn't set opening cash?
        // Let's keep existing logic to avoid breaking feature if used.
        if (this.state.openingCashUSD !== this.pos.pos_session.cash_register_balance_start_mn_ref) {
             this.pos.pos_session.cash_register_balance_start_mn_ref = this.state.openingCashUSD;
             await this.orm.call("pos.session", "set_cashbox_pos_usd", [
                [this.pos.pos_session.id],
                this.state.openingCashUSD,
                this.state.notes || "",
            ]);
        }

        return super.confirm();
    },

    openDetailsPopupUSD() {
        // Decide which logic: Opening or Closing?
        // If cashControl is active and we have default details ref, it's likely closing difference calculation.
        const refId = this.defaultCashDetails?.default_cash_details_ref?.id;
        if (refId) {
             this.state.payments_usd[refId].counted = 0;
             this.state.payments_usd[refId].difference = -this.defaultCashDetails.default_cash_details_ref.amount;
        } else {
             // Fallback to opening cash logic
             this.state.openingCashUSD = 0;
        }
        this.state.displayMoneyDetailsPopupUSD = true;
    },

    closeDetailsPopupUSD() {
        this.state.displayMoneyDetailsPopupUSD = false;
    },

    // Logic from MoneyDetailsPopup.js
    handleInputChangeUSD(paymentId) {
        if (!this.state.payments_usd || !this.state.payments_usd[paymentId]) {
            // Fallback for simple opening input
            this.manualInputCashCountUSD = true;
            if (typeof this.state.openingCashUSD !== "number") {
                this.state.openingCashUSD = 0;
            }
            return;
        }

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
    },

    // Merged update function
    updateCountedCashUSD({ total_ref, moneyDetailsNotesRef }) {
        // If closing details exist
        const refId = this.defaultCashDetails?.default_cash_details_ref?.id;
        if (refId && this.state.payments_usd[refId]) {
            this.state.payments_usd[refId].counted = total_ref;
            this.state.payments_usd[refId].difference = this.pos.round_decimals_currency(
                this.state.payments_usd[refId].counted - this.defaultCashDetails.default_cash_details_ref.amount
            );
        } else {
            // Opening cash logic
             this.state.openingCashUSD = total_ref;
        }

        if (moneyDetailsNotesRef) {
            this.state.notes = (this.state.notes || "") + moneyDetailsNotesRef;
        }
        this.manualInputCashCountUSD = false;
        this.closeDetailsPopupUSD();
    },

    hasDifferenceUSD() {
        return Object.values(this.state.payments_usd || {}).some((pm) => pm.difference != 0);
    },

    hasUserAuthorityUSD() {
        const diffs = Object.values(this.state.payments_usd || {}).map((pm) => Math.abs(pm.difference || 0));
        const maxDiff = diffs.length ? Math.max(...diffs) : 0;
        return this.isManager || this.amountAuthorizedDiffUSD == null || maxDiff <= this.amountAuthorizedDiffUSD;
    },

    // Overriding closeSession to post closing details
    async closeSession() {
        if (this.closeSessionClicked) return;
        this.closeSessionClicked = true;

        try {
            if (this.cashControl && this.defaultCashDetails?.default_cash_details_ref) {
                const refId = this.defaultCashDetails.default_cash_details_ref.id;
                const counted = this.state.payments_usd[refId]?.counted || 0;

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
});

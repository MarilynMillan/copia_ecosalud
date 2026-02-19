/** @odoo-module **/

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { MoneyDetailsPopupUSD } from "./MoneyDetailsPopup";
import { floatIsZero } from "@web/core/utils/numbers";
import { usePos } from "@point_of_sale/app/store/pos_hook";

ClosePosPopup.components = { ...ClosePosPopup.components, MoneyDetailsPopupUSD };

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.pos = usePos();
        this.manualInputCashCountUSD = false;

        this.state.displayMoneyDetailsPopupUSD = false;

        if (this.props.info?.state) {
            Object.assign(this.state, this.props.info.state);
        }
    },

    get amountAuthorizedDiffUSD() {
        return this.props.info.amountAuthorizedDiffUSD || 0;
    },

    hasDifferenceUSD() {
         if (!this.state.payments_usd) return false;
         return Object.values(this.state.payments_usd).some(pm => !floatIsZero(pm.difference, this.pos.currency.decimal_places));
    },

    hasUserAuthorityUSD() {
        const totalDiff = this.calculateTotalDifferenceUSD();
        return Math.abs(totalDiff) <= this.amountAuthorizedDiffUSD;
    },

    calculateTotalDifferenceUSD() {
        if (!this.state.payments_usd) return 0;
        return Object.values(this.state.payments_usd).reduce((acc, pm) => acc + pm.difference, 0);
    },

    async confirm() {
        if (!this.cashControl || !this.hasDifferenceUSD()) {
            return super.confirm();
        }

        if (this.hasUserAuthorityUSD()) {
            const confirmed = await this.popup.add(ConfirmPopup, {
                title: _t("Currency Ref Payments Difference"),
                body: _t("Do you want to accept currency ref payments difference and post a profit/loss journal entry?"),
            });

            if (confirmed) {
                return super.confirm();
            }
        } else {
            await this.popup.add(ConfirmPopup, {
                title: _t("Currency Ref Payments Difference"),
                body: _t(
                    `The maximum difference by currency ref allowed is ${this.pos.format_currency_ref(this.amountAuthorizedDiffUSD)}.
Please contact your manager to accept the closing difference.`
                ),
                confirmText: _t("OK"),
            });
        }
    },

    handleInputChangeUSD(paymentId) {
        const pos = this.pos;

        let expectedAmount;

        if (this.defaultCashDetails && this.defaultCashDetails.default_cash_details_ref && paymentId === this.defaultCashDetails.default_cash_details_ref.id) {
            this.manualInputCashCountUSD = true;
            expectedAmount = this.defaultCashDetails.default_cash_details_ref.amount;
        } else {
            const pm = this.otherPaymentMethods.find(pm => paymentId === pm.id);
            expectedAmount = pm ? pm.amount : 0;
        }

        if (this.state.payments_usd && this.state.payments_usd[paymentId]) {
             this.state.payments_usd[paymentId].difference =
            pos.round_decimals_currency(
                this.state.payments_usd[paymentId].counted - expectedAmount
            );
        }
    },

    async closeSession() {
        if (this.closeSessionClicked) return;

        this.closeSessionClicked = true;
        const pos = this.pos;

        try {
            if (this.cashControl && this.defaultCashDetails && this.defaultCashDetails.default_cash_details_ref) {
                 const paymentRefId = this.defaultCashDetails.default_cash_details_ref.id;
                 if (this.state.payments_usd && this.state.payments_usd[paymentRefId]) {
                    const response = await this.orm.call(
                        "pos.session",
                        "post_closing_cash_details_ref",
                        [pos.pos_session.id],
                        {
                            counted_cash: this.state.payments_usd[paymentRefId].counted,
                        }
                    );

                    if (!response.successful) {
                        this.closeSessionClicked = false;
                        return this.handleClosingError(response);
                    }
                 }
            }

            await this.orm.call(
                "pos.session",
                "update_closing_control_state_session_ref",
                [pos.pos_session.id, this.state.notes]
            );

            super.closeSession();
        } finally {
            this.closeSessionClicked = false;
        }
    },
});

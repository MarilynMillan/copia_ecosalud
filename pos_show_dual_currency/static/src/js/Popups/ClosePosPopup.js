/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";

patch(ClosePosPopup.prototype, {
    setup() {
        super.setup(...arguments);
        // Agregamos nuestras variables al estado ya inicializado por getInitialState
        Object.assign(this.state, {
            displayMoneyDetailsPopupUSD: false,
            // Inicializamos el contador para la moneda de referencia
            payments_usd: {
                [this.props.default_cash_details.default_cash_details_ref?.id]: { 
                    counted: "0",
                    difference: 0 
                }
            }
        });
    },

    //@override
    async confirm() {
        // Primero validamos la moneda principal (lógica nativa)
        if (!this.pos.config.cash_control || (this.env.utils.floatIsZero(this.getMaxDifference()) && !this.hasDifferenceUSD())) {
            await this.closeSession();
            return;
        }

        // Si hay diferencia en USD, validamos autoridad
        if (this.hasUserAuthority() && this.hasUserAuthorityUSD()) {
            const { confirmed } = await this.popup.add("ConfirmPopup", {
                title: _t("Payments Difference (Dual Currency)"),
                body: _t("Do you want to accept the differences in both currencies and close?"),
            });
            if (confirmed) await this.closeSession();
        } else {
            await this.popup.add("ConfirmPopup", {
                title: _t("Difference Too High"),
                body: _t("The difference exceeds your limit. Please contact a manager."),
                confirmText: _t("OK"),
            });
        }
    },

    async openDetailsPopupUSD() {
        const action = _t("USD Cash control - closing");
        // Aquí llamarías a tu MoneyDetailsPopupUSD personalizado
        const { confirmed, payload } = await this.popup.add("MoneyDetailsPopupUSD", {
            moneyDetails: this.moneyDetailsUSD,
            action: action,
        });

        if (confirmed) {
            const { total_ref, moneyDetailsNotesRef, moneyDetails } = payload;
            const refId = this.props.default_cash_details.default_cash_details_ref.id;
            
            this.state.payments_usd[refId].counted = this.pos.format_currency_ref(total_ref, false);
            if (moneyDetailsNotesRef) {
                this.state.notes += "\n" + moneyDetailsNotesRef;
            }
            this.moneyDetailsUSD = moneyDetails;
            this.handleInputChangeUSD(refId);
        }
    },

    handleInputChangeUSD(paymentId) {
        const p = this.state.payments_usd[paymentId];
        const expected = this.props.default_cash_details.default_cash_details_ref.amount;
        p.difference = parseFloat(p.counted || "0") - expected;
    },

    hasDifferenceUSD() {
        const refId = this.props.default_cash_details.default_cash_details_ref?.id;
        return !this.env.utils.floatIsZero(this.state.payments_usd[refId]?.difference || 0);
    },

    hasUserAuthorityUSD() {
        const refId = this.props.default_cash_details.default_cash_details_ref?.id;
        const diff = Math.abs(this.state.payments_usd[refId]?.difference || 0);
        return this.props.is_manager || this.props.amount_authorized_diff == null || diff <= this.props.amount_authorized_diff;
    },

    //@override
    async closeSession() {
        // Antes de llamar al cierre nativo, enviamos los datos de USD al servidor
        if (this.pos.config.cash_control) {
            const refId = this.props.default_cash_details.default_cash_details_ref?.id;
            const countedUSD = parseFloat(this.state.payments_usd[refId]?.counted || "0");

            await this.orm.call("pos.session", "post_closing_cash_details_ref", [
                this.pos.pos_session.id,
                countedUSD,
            ]);
        }
        return super.closeSession();
    }
});
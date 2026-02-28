/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ClosePosPopup.prototype, {
    setup() {
        // 1. Siempre pasar arguments a super.setup
        super.setup(...arguments);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.popup = useService("popup"); // Necesario para showPopup en v17

        this.manualInputCashCountUSD = false;
        
        // 2. IMPORTANTE: Usar Object.assign en lugar de re-declarar this.state
        // Esto mantiene notes, payments, etc., del componente original.
        Object.assign(this.state, {
            displayMoneyDetailsPopupUSD: false,
            // Inicializamos el objeto de pagos USD si no viene en las props
            payments_usd: this.props.info?.state?.payments_usd || {
                [this.props.default_cash_details.default_cash_details_ref?.id]: { counted: 0, difference: 0 }
            }
        });
        
        // Asignamos el resto de la info de las props a la instancia
        Object.assign(this, this.props.info);
    },

    async confirm() {
        // En Odoo 17, el acceso a popups cambió de this.pos.showPopup a this.popup.add
        if (!this.cashControl || !this.hasDifferenceUSD()) {
            return super.confirm();
        } else if (this.hasUserAuthorityUSD()) {
            const confirmed = await this.popup.add("ConfirmPopup", {
                title: this.env._t("Currency Ref Payments Difference"),
                body: this.env._t("Do you want to accept currency ref payments difference and post a profit/loss journal entry?"),
            });
            if (confirmed) return super.confirm();
        } else {
            await this.popup.add("ConfirmPopup", {
                title: this.env._t("Currency Ref Payments Difference"),
                body: this.env._t("The maximum difference by currency ref allowed is %s.\nPlease contact your manager to accept the closing difference.",
                    this.pos.format_currency_ref(this.amountAuthorizedDiffUSD)
                ),
                confirmText: this.env._t("OK"),
            });
        }
    },

    // ... (Tus métodos openDetailsPopupUSD, handleInputChangeUSD, etc. están bien)

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
        } catch (error) {
            this.closeSessionClicked = false;
            throw error; // Deja que Odoo maneje el error de RPC
        }

        return super.closeSession();
    }
});
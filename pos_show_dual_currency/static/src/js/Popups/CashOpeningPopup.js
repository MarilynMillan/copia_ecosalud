/** @odoo-module **/

import { CashOpeningPopup } from "@point_of_sale/app/navbar/cash_opening_popup/cash_opening_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { MoneyDetailsPopupUSD } from "./MoneyDetailsPopup";
import { usePos } from "@point_of_sale/app/store/pos_hook";

CashOpeningPopup.components = { ...CashOpeningPopup.components, MoneyDetailsPopupUSD };

patch(CashOpeningPopup.prototype, {
    setup() {
        super.setup();

        this.orm = useService("orm");
        this.pos = usePos();
        this.manualInputCashCountUSD = null;

        const pos = this.pos;

        Object.assign(this.state, {
            openingCashUSD: pos.pos_session.cash_register_balance_start_mn_ref || 0,
            displayMoneyDetailsPopupUSD: false,
        });
    },

    async confirm() {
        const pos = this.pos;

        // Guardar en objeto local
        pos.pos_session.cash_register_balance_start_mn_ref = this.state.openingCashUSD;

        await this.orm.call("pos.session", "set_cashbox_pos_usd", [
            pos.pos_session.id,
            this.state.openingCashUSD,
            this.state.notes || "",
        ]);

        return super.confirm();
    },

    openDetailsPopupUSD() {
        this.state.openingCashUSD = 0;
        this.state.displayMoneyDetailsPopupUSD = true;
    },

    closeDetailsPopupUSD() {
        this.state.displayMoneyDetailsPopupUSD = false;
    },

    updateCashOpeningUSD({ total_ref, moneyDetailsNotesRef }) {
        this.state.openingCashUSD = total_ref;

        if (moneyDetailsNotesRef) {
            this.state.notes = (this.state.notes || "") + moneyDetailsNotesRef;
        }

        this.manualInputCashCountUSD = false;
        this.closeDetailsPopupUSD();
    },

    handleInputChangeUSD() {
        this.manualInputCashCountUSD = true;

        if (typeof this.state.openingCashUSD !== "number") {
            this.state.openingCashUSD = 0;
        }
    },
});

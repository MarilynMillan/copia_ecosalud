/** @odoo-module */

import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

patch(ClosePosPopup.prototype, {
    
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.manualInputCashCountUSD = null;

        this.state = useState({
            ...this.state, // conserva notes/lo que traiga el base
            openingCashUSD: this.pos.pos_session.cash_register_balance_start_mn_ref || 0,
            displayMoneyDetailsPopupUSD: false,
        });
    }

    async confirm() {
        this.pos.pos_session.cash_register_balance_start_mn_ref = this.state.openingCashUSD;

        await this.orm.call("pos.session", "set_cashbox_pos_usd", [
            [this.pos.pos_session.id],
            this.state.openingCashUSD,
            this.state.notes || "", // <- usamos notes estándar
        ]);

        return super.confirm();
    }

    openDetailsPopupUSD() {
        this.state.openingCashUSD = 0;
        this.state.displayMoneyDetailsPopupUSD = true;
    }

    closeDetailsPopupUSD() {
        this.state.displayMoneyDetailsPopupUSD = false;
    }

    updateCashOpeningUSD({ total_ref, moneyDetailsNotesRef }) {
        this.state.openingCashUSD = total_ref;
        if (moneyDetailsNotesRef) {
            this.state.notes = (this.state.notes || "") + moneyDetailsNotesRef;
        }
        this.manualInputCashCountUSD = false;
        this.closeDetailsPopupUSD();
    }

    handleInputChangeUSD() {
        this.manualInputCashCountUSD = true;
        if (typeof this.state.openingCashUSD !== "number") {
            this.state.openingCashUSD = 0;
        }
    }
}
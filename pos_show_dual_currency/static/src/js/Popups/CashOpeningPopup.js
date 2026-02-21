/** @odoo-module */

import { CashOpeningPopup } from "@point_of_sale/app/utils/cash_opening_popup";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";

export class CashOpeningPopupUSD extends CashOpeningPopup {
    static template = "CashOpeningPopup";

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        this.manualInputCashCountUSD = null;
        this.state = useState({
            openingCash: this.pos.pos_session.cash_register_balance_start || 0,
            openingCashUSD: this.pos.pos_session.cash_register_balance_start_mn_ref || 0,
            displayMoneyDetailsPopupUSD: false,
        });
    }

    async confirm() {
        this.pos.pos_session.cash_register_balance_start_mn_ref = this.state.openingCashUSD;
        await this.rpc({
            model: 'pos.session',
            method: 'set_cashbox_pos_usd',
            args: [this.pos.pos_session.id, this.state.openingCashUSD, this.state.notes_ref],
        });
        super.confirm();
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
            this.state.notes += moneyDetailsNotesRef;
        }
        this.manualInputCashCountUSD = false;
        this.closeDetailsPopupUSD();
    }

    handleInputChangeUSD() {
        this.manualInputCashCountUSD = true;
        if (typeof(this.state.openingCashUSD) !== "number") {
            this.state.openingCashUSD = 0;
        }
    }
}
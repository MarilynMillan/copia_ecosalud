/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { _t } from "@web/core/l10n/translation";

export class CashMovePopupRefCurrency extends AbstractAwaitablePopup {
    static template = "CashMovePopupRefCurrency";

    setup() {
        super.setup();
        this.pos = usePos();
        this.state = useState({
            inputType: 'in', // 'in' or 'out'
            inputAmount: '',
            inputReason: '',
            inputHasError: false,
        });
    }

    onClickButton(type) {
        this.state.inputType = type;
    }

    _onAmountKeypress(ev) {
        if (ev.key === "Enter") {
            this.confirm();
        }
    }

    getPayload() {
        return {
            type: this.state.inputType,
            amount: parseFloat(this.state.inputAmount) || 0,
            reason: this.state.inputReason,
            currency_ref: this.pos.res_currency_ref,
        };
    }
}

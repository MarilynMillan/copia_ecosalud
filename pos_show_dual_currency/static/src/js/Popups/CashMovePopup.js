/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/utils/abstract_awaitable_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useRef, useState } from "@odoo/owl";
import { parseFloat } from "@web/views/fields/parsers";

export class CashMovePopupRefCurrency extends AbstractAwaitablePopup {
    static template = "CashMovePopupRefCurrency";
    static defaultProps = {
        cancelText: _t('Cancel'),
        title: _t('Cash In/Out'),
    };

    setup() {
        super.setup();
        this.state = useState({
            inputType: '',
            inputAmount: '',
            inputReason: '',
            inputHasError: false,
        });
        this.inputAmountRef = useRef('input-amount-ref');
    }

    confirm() {
        try {
            parseFloat(this.state.inputAmount);
        } catch (_error) {
            this.state.inputHasError = true;
            this.errorMessage = this.env._t('Invalid amount');
            return;
        }
        if (this.state.inputType == '') {
            this.state.inputHasError = true;
            this.errorMessage = this.env._t('Select either Cash In or Cash Out before confirming.');
            return;
        }
        if (this.state.inputType === 'out' && this.state.inputAmount > 0) {
            this.state.inputHasError = true;
            this.errorMessage = this.env._t('Insert a negative amount with the Cash Out option.');
            return;
        }
        if (this.state.inputType === 'in' && this.state.inputAmount < 0) {
            this.state.inputHasError = true;
            this.errorMessage = this.env._t('Insert a positive amount with the Cash In option.');
            return;
        }
        if (parseFloat(this.state.inputAmount) < 0) {
            this.state.inputAmount = this.state.inputAmount.substring(1);
        }
        return super.confirm();
    }

    _onAmountKeypress(event) {
        if (event.key === '-') {
            event.preventDefault();
            this.state.inputAmount = this.state.inputType === 'out' ? this.state.inputAmount.substring(1) : `-${this.state.inputAmount}`;
            this.state.inputType = this.state.inputType === 'out' ? 'in' : 'out';
        }
    }

    onClickButton(type) {
        let amount = this.state.inputAmount;
        if (type === 'in') {
            this.state.inputAmount = amount.charAt(0) === '-' ? amount.substring(1) : amount;
        } else {
            this.state.inputAmount = amount.charAt(0) === '-' ? amount : `-${amount}`;
        }
        this.state.inputType = type;
        this.state.inputHasError = false;
        this.inputAmountRef.el && this.inputAmountRef.el.focus();
    }

    getPayload() {
        return {
            amount: parseFloat(this.state.inputAmount),
            reason: this.state.inputReason.trim(),
            type: this.state.inputType,
            currency_ref: this.env.pos.res_currency_ref,
        };
    }
}
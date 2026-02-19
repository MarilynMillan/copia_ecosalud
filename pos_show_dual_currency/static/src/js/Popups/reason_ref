/** @odoo-module **/

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";
import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { useState, useRef } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class CashMovePopupRefCurrency extends AbstractAwaitablePopup {
    static template = "pos_show_dual_currency.CashMovePopupRefCurrency";
    
    static defaultProps = {
        cancelText: _t("Cancel"),
        title: _t("Cash In/Out (USD)"),
    };

    setup() {
        super.setup();
        this.pos = usePos();
        // Cambiamos el nombre de la ref para que coincida con el XML
        this.inputAmountRef = useRef("input-amount-ref"); 
        this.state = useState({
            inputType: '', 
            inputAmount: '',
            inputReason: '',
            inputHasError: false,
            errorMessage: '', // Agregamos esto al state para que sea reactivo
        });
    }

    confirm() {
        this.state.inputHasError = false;
        let amount;
        
        try {
            amount = parseFloat(this.state.inputAmount);
        } catch (_error) {
            this.state.inputHasError = true;
            this.state.errorMessage = _t("Invalid amount");
            return;
        }

        if (!this.state.inputType) {
            this.state.inputHasError = true;
            this.state.errorMessage = _t("Select either Cash In or Cash Out before confirming.");
            return;
        }

        if (this.state.inputType === 'out' && amount > 0) {
            this.state.inputHasError = true;
            this.state.errorMessage = _t("For Cash Out, the amount must be negative.");
            return;
        }

        if (this.state.inputType === 'in' && amount < 0) {
            this.state.inputHasError = true;
            this.state.errorMessage = _t("For Cash In, the amount must be positive.");
            return;
        }

        return super.confirm();
    }

    // Método para formatear el monto mostrado en el botón Confirmar del XML
    format(amount) {
        return this.pos.format_currency_ref(parseFloat(amount) || 0);
    }

    _onAmountKeypress(event) {
        if (event.key === '-') {
            event.preventDefault();
            this.onClickButton(this.state.inputType === 'out' ? 'in' : 'out');
        }
    }

    onClickButton(type) {
        this.state.inputType = type;
        let amount = this.state.inputAmount.toString().replace('-', '');
        
        if (type === 'out' && amount !== '') {
            this.state.inputAmount = `-${amount}`;
        } else {
            this.state.inputAmount = amount;
        }

        this.state.inputHasError = false;
        
        // El foco depende de si usas <Input /> o <input />
        const inputEl = this.inputAmountRef.el?.querySelector('input') || this.inputAmountRef.el;
        if (inputEl) {
            inputEl.focus();
        }
    }

    getPayload() {
        return {
            amount: parseFloat(this.state.inputAmount),
            reason: this.state.inputReason.trim(),
            type: this.state.inputType,
        };
    }
}
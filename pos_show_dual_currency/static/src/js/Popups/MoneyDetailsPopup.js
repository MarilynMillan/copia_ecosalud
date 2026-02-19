/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class MoneyDetailsPopupUSD extends Component {
    static template = "pos_show_dual_currency.MoneyDetailsPopupUSD";

    setup() {
        this.pos = usePos();
        this.currency_ref = this.pos.res_currency_ref;

        const bills = (this.pos.bills || []).filter(b => b.value);

        this.state = useState({
            moneyDetailsRef: Object.fromEntries(
                bills.map(bill => [bill.value, 0])
            ),
            total_ref: 0,
        });

        if (this.props.manualInputCashCountUSD) {
            this.reset();
        }
    }

    // --------- Helpers para dividir columnas ---------

    get firstHalfMoneyDetailsRef() {
        const keys = Object.keys(this.state.moneyDetailsRef)
            .map(Number)
            .sort((a, b) => a - b);

        return keys.slice(0, Math.ceil(keys.length / 2));
    }

    get lastHalfMoneyDetailsRef() {
        const keys = Object.keys(this.state.moneyDetailsRef)
            .map(Number)
            .sort((a, b) => a - b);

        return keys.slice(Math.ceil(keys.length / 2));
    }

    // --------- Cálculo de total ---------

    updateMoneyDetailsAmountRef() {
        const total = Object.entries(this.state.moneyDetailsRef).reduce(
            (acc, [value, qty]) =>
                acc + (parseFloat(value) || 0) * (parseFloat(qty) || 0),
            0
        );

        this.state.total_ref = this.pos.round_decimals_currency(total);
    }

    // --------- Confirmación ---------

    confirm() {
        let moneyDetailsNotesRef = null;

        if (this.state.total_ref) {
            moneyDetailsNotesRef = "Ref Currency Money details:\n";

            (this.pos.bills || []).forEach(bill => {
                const qty = this.state.moneyDetailsRef[bill.value];
                if (qty) {
                    moneyDetailsNotesRef +=
                        `  - ${qty} x ${this.pos.format_currency_ref(bill.value)}\n`;
                }
            });
        }

        const payload = {
            total_ref: this.state.total_ref,
            moneyDetailsNotesRef,
            moneyDetailsRef: { ...this.state.moneyDetailsRef },
        };

        if (this.props.onConfirm) {
            this.props.onConfirm(payload);
        }
    }

    // --------- Reset ---------

    reset() {
        Object.keys(this.state.moneyDetailsRef).forEach(key => {
            this.state.moneyDetailsRef[key] = 0;
        });

        this.state.total_ref = 0;
    }

    // --------- Cancelar ---------

    discard() {
        this.reset();

        if (this.props.onDiscard) {
            this.props.onDiscard();
        }
    }
}
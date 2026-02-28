/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { SaleOrderRow } from "@pos_sale/app/screens/order_management_screen/sale_order_row/sale_order_row";
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate"; // Importamos la utilidad

export class CashMovePopupRefCurrency extends AbstractAwaitablePopup {
    // El nombre del template debe coincidir con el t-name del XML
    static template = "pos_show_dual_currency.CashMovePopupRefCurrency";
    static defaultProps = {
        confirmText: _t("Confirmar"),
        cancelText: _t("Cancelar"),
        title: _t("Movimiento de Efectivo ($)"),
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.inputAmountRef = useRef("input-amount-ref");
        this.state = useState({
            inputType: "in",      // Controla el resaltado de Cash In/Out
            inputAmount: 0,       // Vinculado al t-model del input
            inputReason: "",      // Vinculado al t-model del textarea
            inputHasError: false,
        });
    }

    onClickButton(type) {
        this.state.inputType = type;
    }

    // Se ejecuta al pulsar "Confirm"
    getPayload() {
        return {
            type: this.state.inputType,
            amount: this.state.inputAmount,
            reason: this.state.inputReason,
            currency_ref: true,
        };
    }

    // Manejador para evitar caracteres no numéricos
    _onAmountKeypress(event) {
        if (!/[0-9]/.test(event.key) && event.key !== "." && event.key !== ",") {
            event.preventDefault();
        }
    }
}
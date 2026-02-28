/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
// CORRECCIÓN: La ruta correcta en v17 no incluye static/src y la carpeta se llama 'payment_lines'
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    /**
     * Formatea el monto de la línea de pago en la moneda de referencia.
     * @param {Object} line - Línea de pago
     */
    formatLineAmountUsd(line) {
        if (!line || !this.pos) return "";
        const trm = getRefRate(this.pos);
        const amountRef = line.get_amount() * trm;
        // Usamos el formateador centralizado para consistencia
        return this.pos.format_currency_ref(amountRef);
    },
});
/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_screen_payment_lines/payment_screen_payment_lines";
import { getRefRate, formatNoSymbolRef } from "../../utils/ref_rate";

patch(PaymentScreenPaymentLines.prototype, "pos_show_dual_currency.PaymentLines", {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    // Usado por tu XML (PaymentScreenPaymentLinesDual)
    formatLineAmountUsd(line) {
        const trm = getRefRate(this.pos);
        return formatNoSymbolRef(this.pos, line.get_amount() * trm);
    },
});
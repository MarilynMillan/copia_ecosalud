/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_screen_payment_lines/payment_screen_payment_lines";
import { getRefRate, formatNoSymbolRef } from "../../utils/ref_rate";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    formatLineAmountUsd(line) {
        const trm = getRefRate(this.pos);
        // formatNoSymbolRef needs 'pos' which is available via this.pos
        return formatNoSymbolRef(this.pos, line.get_amount() * trm);
    },
});

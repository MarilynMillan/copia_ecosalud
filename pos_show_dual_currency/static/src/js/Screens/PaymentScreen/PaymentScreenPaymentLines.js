/** @odoo-module **/

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PaymentScreenPaymentLines.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    formatLineAmountUsd(line) {
        const amount = line.get_amount() * this.pos.config.show_currency_rate;
        return this.pos.format_currency_no_symbol(amount);
    }
});

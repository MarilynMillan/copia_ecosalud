/** @odoo-module **/

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenPaymentLines.prototype, {
    formatLineAmountUsd(line) {
        // En v17 usamos 'this.pos' directamente
        const amount = line.get_amount() * this.pos.config.show_currency_rate;
        return this.pos.format_currency_no_symbol(amount);
    }
});

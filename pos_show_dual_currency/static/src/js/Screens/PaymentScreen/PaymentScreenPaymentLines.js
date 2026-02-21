/** @odoo-module */

import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_screen_payment_lines/payment_screen_payment_lines";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class PaymentScreenPaymentLinesDual extends PaymentScreenPaymentLines {
    static template = "PaymentScreenPaymentLinesDual";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    formatLineAmountUsd(line) {
        return this.pos.format_currency_no_symbol(line.get_amount() * this.pos.config.show_currency_rate);
    }
}
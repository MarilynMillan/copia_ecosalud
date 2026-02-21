/** @odoo-module */

import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_screen_status/payment_screen_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class PaymentScreenStatusDual extends PaymentScreenStatus {
    static template = "PaymentScreenStatus";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get remainingTextUSD() {
        return this.pos.format_currency_no_symbol(
            this.props.order.get_due() > 0 ? (this.props.order.get_due() * this.pos.config.show_currency_rate) : 0
        );
    }

    get changeTextUSD() {
        return this.pos.format_currency_no_symbol(this.props.order.get_change() * this.pos.config.show_currency_rate);
    }
}
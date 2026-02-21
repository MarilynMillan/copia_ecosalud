/** @odoo-module **/

import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    get remainingTextUSD() {
        const due = this.props.order.get_due();
        const rate = this.pos.config.show_currency_rate;
        return this.pos.format_currency_no_symbol(due > 0 ? (due * rate) : 0);
    },
    get changeTextUSD() {
        const change = this.props.order.get_change();
        const rate = this.pos.config.show_currency_rate;
        return this.pos.format_currency_no_symbol(change * rate);
    }
});

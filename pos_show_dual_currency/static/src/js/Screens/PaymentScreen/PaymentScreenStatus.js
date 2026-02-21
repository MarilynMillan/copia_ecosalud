/** @odoo-module */

import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreenStatus.prototype, {
    get remainingTextUSD() {
        const order = this.props.order;
        if (!order) return "";
        const rate = this.env.services.pos.config.show_currency_rate;
        if (!rate) return "";
        const remaining = order.get_due() > 0 ? order.get_due() : 0;
        return this.env.services.pos.format_currency_no_symbol(remaining * rate);
    },
    get changeTextUSD() {
        const order = this.props.order;
        if (!order) return "";
        const rate = this.env.services.pos.config.show_currency_rate;
        if (!rate) return "";
        const change = order.get_change();
        return this.env.services.pos.format_currency_no_symbol(change * rate);
    },
    get totalDueTextUSD() {
        const order = this.props.order;
        if (!order) return "";
        const rate = this.env.services.pos.config.show_currency_rate;
        if (!rate) return "";
        return this.env.services.pos.format_currency_no_symbol(order.get_total_with_tax() * rate);
    }
});

/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { getRefRate, formatNoSymbolRef } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos(); 
    },

    get remainingTextUSD() {
        const trm = getRefRate(this.pos);
        const due = this.props.order.get_due() > 0 ? this.props.order.get_due() : 0;
        // Usamos el formateador del pos directamente
        return this.pos.format_currency_ref(due * trm);
    },

    get changeTextUSD() {
        const trm = getRefRate(this.pos);
        const change = this.props.order.get_change() || 0;
        return this.pos.format_currency_ref(change * trm);
    },
});
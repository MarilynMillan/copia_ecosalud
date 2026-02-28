/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { getRefRate, formatNoSymbolRef } from "../../utils/ref_rate";

patch(PaymentScreenStatus.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get remainingTextUSD() {
        const trm = getRefRate(this.pos);
        const due = this.props.order.get_due() > 0 ? this.props.order.get_due() : 0;
        return formatNoSymbolRef(this.pos, due * trm);
    },

    get changeTextUSD() {
        const trm = getRefRate(this.pos);
        return formatNoSymbolRef(this.pos, this.props.order.get_change() * trm);
    },
});

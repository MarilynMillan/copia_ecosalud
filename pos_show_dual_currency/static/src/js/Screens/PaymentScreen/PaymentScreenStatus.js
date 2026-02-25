/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { PaymentScreenStatus } from "@point_of_sale/app/screens/payment_screen/payment_status/payment_status";
import { getRefRate, formatNoSymbolRef } from "../../utils/ref_rate";

patch(PaymentScreenStatus.prototype, {
   

    get remainingTextUSD() {
        // Usamos this.env.pos que es el estándar en componentes v17
        const pos = this.env.pos; 
        const trm = getRefRate(pos);
        const due = this.props.order.get_due() > 0 ? this.props.order.get_due() : 0;
        return formatNoSymbolRef(pos, due * trm);
    },

    get changeTextUSD() {
        const trm = getRefRate(this.pos);
        return formatNoSymbolRef(this.pos, this.props.order.get_change() * trm);
    },
});
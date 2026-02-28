/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { getRefRate } from "../utils/ref_rate";

patch(TicketScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    getTotalUSD(order) {
        if (!order) return "";
        const trm = getRefRate(this.pos);
        const total = order.get_total_with_tax();
        const totalRef = total * trm;
        return this.pos.format_currency_ref ? this.pos.format_currency_ref(totalRef) : totalRef;
    }
});

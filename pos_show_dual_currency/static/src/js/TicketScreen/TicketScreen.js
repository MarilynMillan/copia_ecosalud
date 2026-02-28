/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(TicketScreen.prototype, "pos_show_dual_currency.TicketScreen", {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    getTotalUSD(order) {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(order.get_total_with_tax() * trm);
    },
});
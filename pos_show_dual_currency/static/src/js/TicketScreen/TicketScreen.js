/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(TicketScreen.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    getTotalUSD(order) {
        const rate = this.pos.config.show_currency_rate;
        const trm = rate ? 1 / rate : 0;

        if (trm !== 0) {
            return this.pos.format_currency_ref(order.get_total_with_tax() / trm);
        } else {
            return this.pos.format_currency_ref(order.get_total_with_tax());
        }
    }
});

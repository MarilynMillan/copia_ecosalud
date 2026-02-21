/** @odoo-module */

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class TicketScreenUSD extends TicketScreen {
    static template = "TicketScreen";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    getTotalUSD(order) {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(order.get_total_with_tax() * trm);
    }
}
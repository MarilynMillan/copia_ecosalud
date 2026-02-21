/** @odoo-module */

import { OrderDetails } from "@point_of_sale/app/screens/ticket_screen/order_details/order_details";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderDetailsUSD extends OrderDetails {
    static template = "OrderDetails";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get total_ref() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(this.order ? this.order.get_total_with_tax() * trm : 0);
    }

    get tax_ref() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(this.order ? this.order.get_total_tax() * trm : 0);
    }
}
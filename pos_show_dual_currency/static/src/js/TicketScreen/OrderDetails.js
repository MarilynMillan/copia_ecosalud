/** @odoo-module */

import { OrderDetails } from "@point_of_sale/app/screens/ticket_screen/order_details/order_details";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(OrderDetails.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    get total_ref() {
        const rate = this.pos.config.show_currency_rate;
        const trm = rate ? 1 / rate : 0;
        const order = this.props.order;

        if (trm !== 0) {
            return this.pos.format_currency_ref(order ? order.get_total_with_tax() / trm : 0);
        } else {
            return this.pos.format_currency_ref(order ? order.get_total_with_tax() : 0);
        }
    },
    get tax_ref() {
        const rate = this.pos.config.show_currency_rate;
        const trm = rate ? 1 / rate : 0;
        const order = this.props.order;

        if (trm !== 0) {
            return this.pos.format_currency_ref(order ? order.get_total_tax() / trm : 0);
        } else {
            return this.pos.format_currency_ref(order ? order.get_total_tax() : 0);
        }
    }
});

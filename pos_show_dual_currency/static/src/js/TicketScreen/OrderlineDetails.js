/** @odoo-module */

import { OrderlineDetails } from "@point_of_sale/app/screens/ticket_screen/orderline_details/orderline_details";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(OrderlineDetails.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    get totalPrice_ref() {
        const rate = this.pos.config.show_currency_rate;
        const trm = rate ? 1 / rate : 0;
        const amount = this.props.line.price_subtotal_incl || 0;

        if (trm !== 0) {
            return this.pos.format_currency_ref(amount / trm);
        } else {
            return this.pos.format_currency_ref(amount);
        }
    },

    get unitPrice_ref() {
        const rate = this.pos.config.show_currency_rate;
        const trm = rate ? 1 / rate : 0;
        const amount = this.props.line.price_unit || 0;

        if (trm !== 0) {
            return this.pos.format_currency_ref(amount / trm);
        } else {
            return this.pos.format_currency_ref(amount);
        }
    }
});

/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { OrderDetails } from "@point_of_sale/static/src/app/screens/ticket_screen/ticket_screen";
import { getRefRate } from "../../utils/ref_rate";

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get total_ref() {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.order ? this.order.get_total_with_tax() * trm : 0);
    },

    get tax_ref() {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.order ? this.order.get_total_tax() * trm : 0);
    },
});
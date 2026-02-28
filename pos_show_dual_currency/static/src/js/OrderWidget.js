/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/screens/product_screen/order_widget/order_widget";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { getRefRate } from "./utils/ref_rate";

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get total_ref() {
        // En v17, el pos suele estar disponible en this.pos o this.env.pos
        const order = this.pos.get_order();
        const refRate = getRefRate(this.pos);
        const totalRef = (order ? order.get_total_with_tax() : 0) * refRate;
        // Check if format_currency_ref exists (patched in models.js)
        return this.pos.format_currency_ref ? this.pos.format_currency_ref(totalRef) : totalRef;
    },

    get tax_ref() {
        const order = this.pos.get_order();
        const trm = getRefRate(this.pos);
        const taxRef = (order ? order.get_total_tax() : 0) * trm;
        return this.pos.format_currency_ref ? this.pos.format_currency_ref(taxRef) : taxRef;
    }
});

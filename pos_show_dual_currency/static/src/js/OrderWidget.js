/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { OrderWidget } from "@point_of_sale/app/screens/product_screen/order_widget/order_widget";
import { getRefRate } from "../utils/ref_rate";

patch(OrderWidget.prototype, {
    get total_ref() {
        // En v17, el pos suele estar disponible en this.pos o this.env.pos
        const order = this.pos.get_order();
        const refRate = getRefRate(this.pos);
        const totalRef = (order ? order.get_total_with_tax() : 0) * refRate;
        return this.pos.format_currency_ref(totalRef);
    },
});
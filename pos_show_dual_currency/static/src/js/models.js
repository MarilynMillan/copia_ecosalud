/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.show_dual_currency) {
            const rate = this.pos.config.show_currency_rate;
            if (rate) {
                result.total_with_tax_sec = this.get_total_with_tax() * rate;
                result.change_sec = this.get_change() * rate;
            } else {
                 result.total_with_tax_sec = 0;
                 result.change_sec = 0;
            }
        }
        return result;
    },
});

patch(Orderline.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.show_dual_currency) {
             const rate = this.pos.config.show_currency_rate;
             if (rate) {
                // Using get_price_with_tax() as it returns the total price for the line including tax
                result.price_with_tax_sec = this.get_price_with_tax() * rate;
             } else {
                result.price_with_tax_sec = 0;
             }
        }
        return result;
    },
});

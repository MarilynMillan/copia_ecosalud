/** @odoo-module */

import { Payment } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Payment.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.show_dual_currency) {
            result.amount_sec = this.get_amount() * this.pos.config.show_currency_rate;
        }
        return result;
    },
});

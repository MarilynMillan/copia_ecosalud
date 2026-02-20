/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    get_change_sec() {
        if (!this.pos.config.show_dual_currency) return 0;
        const rate = this.pos.config.show_currency_rate;
        return this.get_change() * rate;
    },
    get_total_with_tax_sec() {
        if (!this.pos.config.show_dual_currency) return 0;
        const rate = this.pos.config.show_currency_rate;
        return this.get_total_with_tax() * rate;
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        if (this.pos.config.show_dual_currency) {
            result.change_sec = this.get_change_sec();
            result.total_with_tax_sec = this.get_total_with_tax_sec();
            result.currency_sec_rate = this.pos.config.show_currency_rate;
        }
        return result;
    },
});

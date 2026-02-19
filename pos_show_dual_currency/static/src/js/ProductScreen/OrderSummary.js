/** @odoo-module **/

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";

patch(OrderSummary.prototype, {
    getTaxRef() {
        const trm = 1 / this.env.pos.config.show_currency_rate;
        const total = this.props.order.get_total_with_tax();
        const totalWithoutTax = this.props.order.get_total_without_tax();

        let taxAmount = 0;
        if (trm !== 0) {
            taxAmount = (total - totalWithoutTax) / trm;
        }

        return {
            hasTax: !floatIsZero(
                taxAmount,
                this.env.pos.currency.decimal_places
            ),
            displayAmount: this.env.pos.format_currency_ref(taxAmount),
        };
    },
});

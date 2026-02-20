/** @odoo-module **/

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";

patch(OrderWidget.prototype, {
    getTaxRef() {
        const pos = this.env.services.pos;
        const trm = 1 / pos.config.show_currency_rate;
        // In Odoo 17 OrderWidget usually receives order lines, not necessarily the order object directly as props.order
        // But often it has `props.total` or similar.
        // Let's assume props.order is available or use pos.get_order()
        const order = this.props.order || pos.get_order();
        if (!order) return { hasTax: false, displayAmount: "" };

        const total = order.get_total_with_tax();
        const totalWithoutTax = order.get_total_without_tax();

        let taxAmount = 0;
        if (trm !== 0) {
            taxAmount = (total - totalWithoutTax) / trm;
        }

        return {
            hasTax: !floatIsZero(
                taxAmount,
                pos.currency.decimal_places
            ),
            displayAmount: pos.format_currency_ref(taxAmount),
        };
    },
});

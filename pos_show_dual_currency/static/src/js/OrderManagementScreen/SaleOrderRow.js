/** @odoo-module */

import { SaleOrderRow } from "@pos_sale/app/screens/sale_order_list/sale_order_row/sale_order_row";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(SaleOrderRow.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    get total_ref() {
        const trm = 1 / this.pos.config.show_currency_rate;
        if (trm !== 0) {
            return this.pos.format_currency_ref(this.props.order.amount_total / trm);
        } else {
            return this.pos.format_currency_ref(this.props.order.amount_total);
        }
    },
    get showAmountUnpaid_ref() {
        const order = this.props.order;
        const difference = order.amount_total - order.amount_unpaid;

        // Assuming res_currency_ref is set in PosStore via models.js
        const currency = this.pos.res_currency_ref || this.pos.currency;
        const decimalPlaces = currency.decimal_places;

        let isFullAmountUnpaid = floatIsZero(Math.abs(difference), decimalPlaces);

        const trm = 1 / this.pos.config.show_currency_rate;

        if (trm !== 0) {
            isFullAmountUnpaid = floatIsZero(Math.abs(difference / trm), decimalPlaces);
            return !isFullAmountUnpaid && !floatIsZero(order.amount_unpaid * trm, decimalPlaces);
        } else {
            return !isFullAmountUnpaid && !floatIsZero(order.amount_unpaid, decimalPlaces);
        }
    }
});

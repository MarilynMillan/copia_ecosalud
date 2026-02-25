/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { SaleOrderRow } from "@pos_sale/app/screens/order_management_screen/sale_order_row/sale_order_row";
import { getRefRate } from "../../utils/ref_rate"; // Importamos la utilidad

patch(SaleOrderRow.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },

    get total_ref() {
        const trm = getRefRate(this.pos);
        // Usamos this.props.order en lugar de this.order
        return this.pos.format_currency_ref(this.props.order.amount_total * trm);
    },

    get showAmountUnpaid_ref() {
        const trm =
            this.pos.pos_session?.tax_today ||
            (this.pos.config.show_currency_rate ? 1 / this.pos.config.show_currency_rate : 1);

        const precision = this.pos.res_currency_ref?.decimal_places || 2;

        const difference = this.order.amount_total - this.order.amount_unpaid;
        const isFullAmountUnpaidRef = floatIsZero(Math.abs(difference * trm), precision);

        return (
            !isFullAmountUnpaidRef &&
            !floatIsZero(this.order.amount_unpaid * trm, precision)
        );
    },
});
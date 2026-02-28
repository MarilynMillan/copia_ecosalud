/** @odoo-module */

// Usamos exactamente la ruta que encontraste en SaleOrderList
import { SaleOrderRow } from "@pos_sale/app/order_management_screen/sale_order_row/sale_order_row";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(SaleOrderRow.prototype, {
    setup() {
        super.setup(...arguments);
        // Inyectamos el store para tener acceso a format_currency_ref
        this.pos = usePos();
    },

    get total_ref() {
        const trm = getRefRate(this.pos);
        // Accedemos al order desde props
        const total = this.props.order.amount_total || 0;
        return this.pos.format_currency_ref(total * trm);
    },

    get amount_unpaid_ref() {
        const trm = getRefRate(this.pos);
        const unpaid = this.props.order.amount_unpaid || 0;
        return this.pos.format_currency_ref(unpaid * trm);
    },

    get showAmountUnpaid_ref() {
        const trm = getRefRate(this.pos);
        const precision = this.pos.res_currency_ref?.decimal_places || 2;
        const order = this.props.order;

        const difference = order.amount_total - order.amount_unpaid;

        // Validamos si la diferencia es cero en la moneda de referencia
        const isFullAmountUnpaidRef = floatIsZero(Math.abs(difference * trm), precision);

        return (
            !isFullAmountUnpaidRef &&
            !floatIsZero(order.amount_unpaid * trm, precision)
        );
    }
});
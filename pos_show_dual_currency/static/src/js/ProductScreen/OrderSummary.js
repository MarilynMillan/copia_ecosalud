/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { getRefRate } from "../../utils/ref_rate";

// Eliminamos "pos_show_dual_currency.OrderSummary"
patch(OrderSummary.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    getTaxRef() {
        const trm = getRefRate(this.pos);
        const total = this.props.order.get_total_with_tax();
        const totalWithoutTax = this.props.order.get_total_without_tax();
        const taxAmountRef = (total - totalWithoutTax) * trm;

        const precision = (this.pos.res_currency_ref?.decimal_places ?? this.pos.currency.decimal_places);

        return {
            hasTax: !floatIsZero(taxAmountRef, precision),
            displayAmount: this.pos.format_currency_ref(taxAmountRef),
        };
    },

    // Agregamos el total general en USD para que lo puedas usar en el XML
    get totalUSD() {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.props.order.get_total_with_tax() * trm);
    }
});
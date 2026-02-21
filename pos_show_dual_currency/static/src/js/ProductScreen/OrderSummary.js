/** @odoo-module */

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";

export class OrderSummaryUSD extends OrderSummary {
    static template = "OrderSummary";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    getTaxRef() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        const total = this.props.order.get_total_with_tax();
        const totalWithoutTax = this.props.order.get_total_without_tax();
        const taxAmount = (total - totalWithoutTax) * trm;
        
        return {
            hasTax: !floatIsZero(taxAmount, this.pos.currency.decimal_places),
            displayAmount: this.pos.format_currency_ref(taxAmount),
        };
    }
}
/** @odoo-module */

import { SaleOrderRow } from "@pos_sale/app/screens/order_management_screen/sale_order_row/sale_order_row";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { floatIsZero } from "@web/core/utils/numbers";

export class SaleOrderRowUSD extends SaleOrderRow {
    static template = "SaleOrderRow";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get total_ref() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(this.order.amount_total * trm);
    }

    get showAmountUnpaid_ref() {
        const difference = this.order.amount_total - this.order.amount_unpaid;
        const isFullAmountUnpaid = floatIsZero(Math.abs(difference), this.pos.show_currency.decimal_places);
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        
        const isFullAmountUnpaidRef = floatIsZero(Math.abs(difference * trm), this.pos.show_currency.decimal_places);
        return !isFullAmountUnpaidRef && !floatIsZero(this.order.amount_unpaid * trm, this.pos.show_currency.decimal_places);
    }
}
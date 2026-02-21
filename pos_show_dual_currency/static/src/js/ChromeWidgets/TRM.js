/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { formatCurrency } from "@web/core/currency";

export class TRM extends Component {
    static template = "TRM";
    
    setup() {
        this.pos = usePos();
    }

    get trm() {
        return formatCurrency(
            1 / this.pos.config.show_currency_rate,
            this.pos.currency.name,
            this.pos.currency.decimal_places
        );
    }
}
/** @odoo-module */

import { Component } from "@odoo/owl";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { usePos } from "@point_of_sale/app/store/pos_store"; // Importación correcta
import { formatCurrency } from "@web/core/currency";

export class TRM extends Component {
    static template = "pos_show_dual_currency.TRM";

    setup() {
        this.pos = usePos();
    }

    get trm() {
        const rate = this.pos.config.show_currency_rate || 0;
        const trmValue = rate ? 1 / rate : 1;
        // formatCurrency espera (amount, currencyObject)
        return formatCurrency(trmValue, this.pos.currency);
    }
}
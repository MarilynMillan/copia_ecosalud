/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Navbar } from "@point_of_sale/app/navbar/navbar";

export class TRM extends Component {
    static template = "TRM";
    setup() {
        this.pos = usePos();
    }
    get trm() {
        const rate = this.pos.config.show_currency_rate;
        if (!rate) return "N/A";
        return this.pos.format_currency_no_symbol(1 / rate);
    }
}

// Register TRM in Navbar components
Navbar.components = { ...Navbar.components, TRM };

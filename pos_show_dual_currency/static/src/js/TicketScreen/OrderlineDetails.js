/** @odoo-module */

import { OrderlineDetails } from "@point_of_sale/app/screens/ticket_screen/orderline_details/orderline_details";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class OrderlineDetailsUSD extends OrderlineDetails {
    static template = "OrderlineDetails";

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get totalPrice_ref() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(this.line.totalPrice * trm);
    }

    get unitPrice_ref() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        return this.pos.format_currency_ref(this.line.unitPrice * trm);
    }

    get pricePerUnit() {
        const trm = this.pos.config.show_currency_rate !== 0 ? 1 / this.pos.config.show_currency_rate : 1;
        const unitPriceRef = this.pos.format_currency_ref(this.line.unitPrice * trm);
        return ` ${this.unit} at ${this.unitPrice} - ${unitPriceRef} / ${this.unit}`;
    }
}
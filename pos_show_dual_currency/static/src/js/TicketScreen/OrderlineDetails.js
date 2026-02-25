/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Orderline } from "@point_of_sale/app/generic_components/orderline/orderline";
import { getRefRate } from "../../utils/ref_rate";

patch(OrderlineDetails.prototype, "pos_show_dual_currency.TicketOrderlineDetails", {
    setup() {
        super.setup();
        this.pos = usePos();
    },

    get totalPrice_ref() {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.line.totalPrice * trm);
    },

    get unitPrice_ref() {
        const trm = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.line.unitPrice * trm);
    },

    get pricePerUnit() {
        const trm = getRefRate(this.pos);
        const unitPriceRef = this.pos.format_currency_ref(this.line.unitPrice * trm);
        return ` ${this.unit} at ${this.unitPrice} - ${unitPriceRef} / ${this.unit}`;
    },
});
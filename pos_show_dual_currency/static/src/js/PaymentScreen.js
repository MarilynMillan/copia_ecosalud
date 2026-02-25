/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { getRefRate } from "../../utils/ref_rate";

ppatch(PaymentScreen.prototype, {
    get total_with_tax_ref() {
        const refRate = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.currentOrder.get_total_with_tax() * refRate);
    },
    get total_due_ref() {
        const refRate = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.currentOrder.get_due() * refRate);
    },
    get total_paid_ref() {
        const refRate = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.currentOrder.get_total_paid() * refRate);
    },
    get total_change_ref() {
        const refRate = getRefRate(this.pos);
        return this.pos.format_currency_ref(this.currentOrder.get_change() * refRate);
    },
});
/** @odoo-module */

// 1. Importaciones de Odoo v17
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

// 2. Parche para la LÓGICA (el .js)
//    (Tu código original de 'PaymentScreen.js' es 100% compatible)
patch(PaymentScreen.prototype, {
    get total_sec() {
        return this.pos.get_order().get_total_with_tax_sec();
    },
    get total_due_sec() {
        return this.currentOrder.get_due() * this.pos.currency_sec_rate;
    },
    get total_paid_sec() {
        return this.currentOrder.get_total_paid() * this.pos.currency_sec_rate;
    },
    get total_change_sec() {
        return this.currentOrder.get_change() * this.pos.currency_sec_rate;
    }
});
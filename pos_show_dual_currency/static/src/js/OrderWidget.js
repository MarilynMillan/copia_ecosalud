/** @odoo-module */

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook"; // Importación necesaria
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(OrderWidget.prototype, {
    setup() {
        super.setup(...arguments);
        // INYECCIÓN CRÍTICA: Sin esto, 'this.pos' no existe en este componente
        this.pos = usePos(); 
    },

    get total_ref() {
        // Ahora 'this.pos' ya no es undefined
        const order = this.pos?.get_order();
        if (!order) {
            return "";
        }

        const refRate = getRefRate(this.pos);
        const totalRef = order.get_total_with_tax() * refRate;

        return this.pos.format_currency_ref(totalRef);
    },
});
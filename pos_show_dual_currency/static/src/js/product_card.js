/** @odoo-module */

import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { getRefRate } from "@pos_show_dual_currency/js/utils/ref_rate";

patch(ProductCard.prototype, {
    setup() {
        super.setup(...arguments);
        // Inyectamos el store para que el XML pueda leer 'pos.config'
        this.pos = usePos();
    },

    get price_ref() {
        const trm = getRefRate(this.pos);
        // En ProductCard, el producto viene en this.props
        const price = this.props.price || 0;
        return this.pos.format_currency_ref(price * trm);
    }
});
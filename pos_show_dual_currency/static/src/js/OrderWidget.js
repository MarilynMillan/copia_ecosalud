/** @odoo-module */

// 1. Importaciones de Odoo v17
import { OrderWidget } from "@point_of_sale/app/screens/product_screen/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { xml } from "@odoo/owl"; // Importamos 'xml'

// 2. Parche para la LÓGICA (el .js)
//    (Tu código original de 'OrderWidget.js')
patch(OrderWidget.prototype, {
    get total_sec() {
        return this.pos.get_order().get_total_with_tax_sec();
    },
});

// 3. Parche para la PLANTILLA (el .xml)
//    (Este es el reemplazo de la parte de 'pos.xml' que modifica el OrderWidget)
patch(OrderWidget, {
    template: xml`
        <t t-patch="OrderWidget" t-patch-mode="append">
            <xpath expr="//div[hasclass('subtotal')]" position="after">
                <div class="subtotal">
                    <span class="label">Total Sec:</span>
                    <span class="price">
                        <t t-esc="env.pos.format_currency_no_symbol(total_sec)"/>
                    </span>
                </div>
            </xpath>
        </t>
    `,
});
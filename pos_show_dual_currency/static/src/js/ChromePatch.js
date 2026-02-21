/** @odoo-module */

// 1. Importaciones de Odoo v17
import { Chrome } from "@point_of_sale/app/pos_hook"; // Se importa 'Chrome' desde 'pos_hook'
import { patch } from "@web/core/utils/patch";
import { xml } from "@odoo/owl"; // Importamos 'xml'
import { TRM } from "./ChromeWidgets/TRM.js"; // Importamos tu widget TRM migrado

// 2. Parche para la LÓGICA (el .js)
//    Añadimos el componente TRM a los componentes del Chrome
patch(Chrome.prototype, {
    get components() {
        // Añadimos TRM a la lista de componentes
        return { ...super.components, TRM };
    }
});

// 3. Parche para la PLANTILLA (el .xml)
//    (Este es el reemplazo de 'Chrome.xml')
patch(Chrome, {
    template: xml`
        <t t-patch="Chrome" t-patch-mode="append">
            <xpath expr="//div[hasclass('pos-header-right')]" position="inside">
                <TRM />
            </xpath>
        </t>
    `,
});
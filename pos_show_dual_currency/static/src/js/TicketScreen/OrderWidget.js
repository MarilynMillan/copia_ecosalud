/** @odoo-module **/

import { OrderWidget } from "@point_of_sale/app/generic_components/order_widget/order_widget";
import { patch } from "@web/core/utils/patch";
import { onPatched, onMounted } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";

patch(OrderWidget.prototype, {
    setup() {
        super.setup();
        onMounted(this._updateDualCurrency.bind(this));
        onPatched(this._updateDualCurrency.bind(this));
    },

    _updateDualCurrency() {
        const order = this.props.order || (this.env.pos && this.env.pos.get_order());
        if (!order) return;

        const total = order.get_total_with_tax();
        const taxes = total - order.get_total_without_tax();

        if (this.env.pos.config.show_dual_currency) {
            let total_currency = 0;
            let taxes_currency = 0;
            const rate_company = parseFloat(this.env.pos.config.rate_company || 1);
            const show_currency_rate = parseFloat(this.env.pos.config.show_currency_rate || 1);

            if (rate_company > show_currency_rate) {
                total_currency = total * show_currency_rate;
                taxes_currency = taxes * show_currency_rate;
            } else if (rate_company < show_currency_rate) {
                if (show_currency_rate > 0) {
                    total_currency = total * show_currency_rate;
                    taxes_currency = taxes * show_currency_rate;
                }
            } else {
                total_currency = total;
                taxes_currency = taxes;
            }

            // Manipulación del DOM para compatibilidad con tu vista XML personalizada
            // Nota: En Odoo 17 se recomienda usar t-esc en el XML en lugar de esto
            const el = this.el; 
            if (el) {
                const valueEl = el.querySelector('.value');
                if (valueEl) valueEl.textContent = this.env.pos.format_currency(total);
                
                const valueCurrencyEl = el.querySelector('.value_currency');
                if (valueCurrencyEl) valueCurrencyEl.textContent = '$' + this.env.pos.format_currency_no_symbol(total_currency);
                
                const valueTaxEl = el.querySelector('.value_tax');
                if (valueTaxEl) valueTaxEl.textContent = this.env.pos.format_currency(taxes);
                
                const valueCurrencyTaxEl = el.querySelector('.value_currency_tax');
                if (valueCurrencyTaxEl) valueCurrencyTaxEl.textContent = '$' + this.env.pos.format_currency_no_symbol(taxes_currency);
            }
        }
    }
});

/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";


patch(PosStore.prototype, {
    /**
     * 1. Procesamiento de datos con validaciones de seguridad.
     * Adaptado para Odoo 17 para recibir la lista de monedas correctamente.
     */
    async _processData(loadedData) {
        await super._processData(...arguments);
        
        // Obtenemos la data del loader específico definido en Python
        const currencyData = loadedData["res.currency.ref"];

        // SEGURIDAD: Verificamos que sea un arreglo con datos
        if (Array.isArray(currencyData) && currencyData.length > 0) {
            // Asignamos el primer elemento (la moneda encontrada)
            this.res_currency_ref = currencyData[0];
        } else {
            // Fallback a la moneda base de la sesión para evitar que format_currency_ref falle
            this.res_currency_ref = this.currency;
        }
    },

    /**
     * 2. Formateador de moneda optimizado.
     * Utiliza el motor nativo de Odoo 17 pasando el objeto moneda completo.
     */
    format_currency_ref(amount) {
        const cur = this.res_currency_ref || this.currency;
        // format_currency(monto, con_simbolo, objeto_moneda)
        return this.format_currency(amount, true, cur);
    },

    /**
     * 3. Adaptación de Cierre de Caja.
     * Inyecta la lógica de moneda dual en el estado del popup de cierre.
     */
    async getClosePosInfo() {
        const info = await super.getClosePosInfo();
        
        try {
            const closingData = await this.orm.call(
                "pos.session", 
                "get_closing_control_data", 
                [[this.pos_session.id]]
            );

            const amountAuthorizedDiffUSD = closingData?.amount_authorized_diff_ref || 0;

            const state_new = {
                notes: "",
                acceptClosing: false,
                payments: {},
                payments_usd: {},
            };

            if (info.cashControl && info.defaultCashDetails) {
                state_new.payments[info.defaultCashDetails.id] = {
                    counted: 0,
                    difference: -info.defaultCashDetails.amount,
                    number: 0,
                };
                
                // Mapeo de moneda secundaria en el cierre (USD/Referencia)
                const ref = closingData?.default_cash_details?.default_cash_details_ref;
                if (ref?.id) {
                    state_new.payments_usd[ref.id] = {
                        counted: 0,
                        difference: -ref.amount,
                        number: 0,
                    };
                }
            }

            // Retornamos la info original extendida con nuestro nuevo estado y diferencias
            return { ...info, state: state_new, amountAuthorizedDiffUSD };
        } catch (error) {
            console.error("Error cargando datos de cierre dual:", error);
            // Si el servicio falla, devolvemos la info base para no bloquear el cierre del POS
            return info;
        }
    },
});
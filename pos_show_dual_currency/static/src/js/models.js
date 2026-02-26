/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";
import { getRefRate } from "./utils/ref_rate";

patch(PosStore.prototype, {
    setup() {
        super.setup(...arguments);
        this.res_currency_ref = null;
    },

    async _processData(loadedData) {
        await super._processData(loadedData);
        // 'pos.session' data contains our injected 'res_currency_ref'
        if (loadedData['pos.session'] && loadedData['pos.session'].res_currency_ref) {
             this.res_currency_ref = loadedData['pos.session'].res_currency_ref;
        } else {
             // Fallback if not nested (or if my assumption about nesting was wrong and it IS at root)
             this.res_currency_ref = loadedData.res_currency_ref;
        }
    },

    format_currency_no_symbol(amount, precision, currency) {
        return formatFloat(amount, { digits: [precision, precision] });
    },

    format_currency_ref(amount) {
        const cur = this.res_currency_ref;
        if (!cur) return this.format_currency(amount);

        const num = this.format_currency_no_symbol(amount, cur.decimal_places, cur);
        return cur.position === "after"
            ? `${num} ${cur.symbol || ""}`.trim()
            : `${cur.symbol || ""} ${num}`.trim();
    },

    async getClosePosInfo() {
        // En Odoo 17, si getClosePosInfo no existe en el padre con la misma firma o comportamiento,
        // hay que tener cuidado. En v17 standard, getClosePosInfo devuelve info para el popup.
        // Aquí asumimos que la lógica es similar.
        const info = await super.getClosePosInfo();

        const closingData = await this.orm.call("pos.session", "get_closing_control_data", [[this.pos_session.id]]);
        const amountAuthorizedDiffUSD = closingData.amount_authorized_diff_ref;

        const state_new = {
            notes: "",
            acceptClosing: false,
            payments: {},
            payments_usd: {},
        };

        if (info.cashControl) {
            state_new.payments[info.defaultCashDetails.id] = {
                counted: 0,
                difference: -info.defaultCashDetails.amount,
                number: 0,
            };
            const ref = info.defaultCashDetails.default_cash_details_ref;
            if (ref && ref.id) {
                state_new.payments_usd[ref.id] = {
                    counted: 0,
                    difference: -ref.amount,
                    number: 0,
                };
            }
        }

        if (info.otherPaymentMethods && info.otherPaymentMethods.length) {
            info.otherPaymentMethods.forEach((pm) => {
                if (pm.type === "bank") {
                    state_new.payments[pm.id] = {
                        counted: this.round_decimals_currency(pm.amount),
                        difference: 0,
                        number: pm.number,
                    };
                }
            });
        }

        return { ...info, state: state_new, amountAuthorizedDiffUSD };
    },
});

patch(Order.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        const trm = getRefRate(this.pos);
        result.total_with_tax_ref = this.pos.format_currency_ref(this.get_total_with_tax() * trm);
        result.total_tax_ref = this.pos.format_currency_ref(this.get_total_tax() * trm);
        result.amount_total_ref = this.get_total_with_tax() * trm;
        return result;
    },
});

patch(Orderline.prototype, {
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        const trm = getRefRate(this.pos);
        result.price_display_ref = this.pos.format_currency_ref(this.get_display_price() * trm);
        result.price_with_tax_ref = this.pos.format_currency_ref(this.get_price_with_tax() * trm);
        result.price_without_tax_ref = this.pos.format_currency_ref(this.get_price_without_tax() * trm);
        result.price_ref = this.pos.format_currency_ref(this.get_unit_display_price() * trm);
        return result;
    },
});

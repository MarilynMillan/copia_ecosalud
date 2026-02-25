/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { formatFloat } from "@web/core/utils/numbers";
import { renderToString } from "@web/core/utils/render";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.res_currency_ref = null;
    },

    async _processData(loadedData) {
        await super._processData(loadedData);
        this.res_currency_ref = loadedData.res_currency_ref;
    },

    format_currency_no_symbol(amount, precision, currency) {
        // Simple formatter without symbol
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
        // Calls orm which is this.orm (from service)
        // PosStore in 17 has this.orm? Usually yes.
        const closingData = await this.orm.call("pos.session", "get_closing_control_data", [[this.pos_session.id]]);
        const amountAuthorizedDiffUSD = closingData.amount_authorized_diff_ref;

        const info = await super.getClosePosInfo();

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
            if (ref?.id) {
                state_new.payments_usd[ref.id] = {
                    counted: 0,
                    difference: -ref.amount,
                    number: 0,
                };
            }
        }

        if (info.otherPaymentMethods?.length) {
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

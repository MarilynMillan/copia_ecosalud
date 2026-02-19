/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    // @override
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.res_currency_ref = loadedData['res_currency_ref'];
    },

    format_currency_ref(amount) {
        amount = this.format_currency_no_symbol(amount, this.res_currency_ref.decimal_places, this.res_currency_ref);
        if (this.res_currency_ref.position === 'after') {
            return amount + ' ' + (this.res_currency_ref.symbol || '');
        } else {
            return (this.res_currency_ref.symbol || '') + ' ' + amount;
        }
    },

    async getClosePosInfo() {
        const closingData = await this.env.services.orm.call(
            'pos.session',
            'get_closing_control_data',
            [[this.pos_session.id]]
        );
        const amountAuthorizedDiffUSD = closingData.amount_authorized_diff_ref;

        const info = await super.getClosePosInfo();
        const state_new = {notes: '', acceptClosing: false, payments: {}, notes_ref: '', acceptClosing_usd: false, payments_usd: {}};

        if (info.cashControl) {
            state_new.payments[info.defaultCashDetails.id] = {counted: 0, difference: -info.defaultCashDetails.amount, number: 0};
            if (info.defaultCashDetails.default_cash_details_ref) {
                 state_new.payments_usd[info.defaultCashDetails.default_cash_details_ref.id] = {counted: 0, difference: -info.defaultCashDetails.default_cash_details_ref.amount, number: 0};
            }
        }

        if (info.otherPaymentMethods.length > 0) {
            info.otherPaymentMethods.forEach(pm => {
                if (pm.type === 'bank') {
                    state_new.payments[pm.id] = {counted: this.round_decimals_currency(pm.amount), difference: 0, number: pm.number}
                }
            })
        }

        // Return the modified info object
        return {
            ...info,
            state: state_new,
            amountAuthorizedDiffUSD: amountAuthorizedDiffUSD
        };
    }
});

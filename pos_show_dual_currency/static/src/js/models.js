/** @odoo-module */

import { PosGlobalState } from "@point_of_sale/app/models/pos_global_state";
import { registry } from "@point_of_sale/app/store/registries";
import { _t } from "@web/core/l10n/translation";

export class CurrencyRefPosGlobalState extends PosGlobalState {
    static serviceDependencies = [...PosGlobalState.serviceDependencies];

    setup() {
        super.setup();
        this.res_currency_ref = null;
    }

    async _processData(loadedData) {
        await super._processData(loadedData);
        this.res_currency_ref = loadedData['res_currency_ref'];
    }

    format_currency_ref(amount) {
        amount = this.format_currency_no_symbol(amount, this.res_currency_ref.decimal_places, this.res_currency_ref);
        if (this.res_currency_ref.position === 'after') {
            return amount + ' ' + (this.res_currency_ref.symbol || '');
        } else {
            return (this.res_currency_ref.symbol || '') + ' ' + amount;
        }
    }

    async getClosePosInfo() {
        const closingData = await this.orm.call(
            'pos.session',
            'get_closing_control_data',
            [[this.pos_session.id]]
        );
        const amountAuthorizedDiffUSD = closingData.amount_authorized_diff_ref;

        const info = await super.getClosePosInfo();
        const state_new = {
            notes: '', 
            acceptClosing: false, 
            payments: {}, 
            notes_ref: '', 
            acceptClosing_usd: false, 
            payments_usd: {}
        };
        
        if (info.cashControl) {
            state_new.payments[info.defaultCashDetails.id] = {
                counted: 0, 
                difference: -info.defaultCashDetails.amount, 
                number: 0
            };
            state_new.payments_usd[info.defaultCashDetails.default_cash_details_ref.id] = {
                counted: 0, 
                difference: -info.defaultCashDetails.default_cash_details_ref.amount, 
                number: 0
            };
        }

        if (info.otherPaymentMethods.length > 0) {
            info.otherPaymentMethods.forEach(pm => {
                if (pm.type === 'bank') {
                    state_new.payments[pm.id] = {
                        counted: this.round_decimals_currency(pm.amount), 
                        difference: 0, 
                        number: pm.number
                    };
                }
            });
        }

        return {
            ...info,
            state: state_new,
            amountAuthorizedDiffUSD
        };
    }
}

registry.category("pos_global_state_models").add("CurrencyRefPosGlobalState", CurrencyRefPosGlobalState);
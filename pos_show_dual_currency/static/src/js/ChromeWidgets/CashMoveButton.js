/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const TRANSLATED_CASH_MOVE_TYPE = {
    in: _t('in'),
    out: _t('out'),
};

export class CashMoveButtonRefCurrency extends Component {
    static template = "CashMoveButtonRefCurrency";

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.rpc = useService("rpc");
    }

    async onClickUSD() {
        const { confirmed, payload } = await this.pos.showPopup('CashMovePopupRefCurrency');
        if (!confirmed) return;
        const { type, amount, reason, currency_ref } = payload;
        const translatedType = TRANSLATED_CASH_MOVE_TYPE[type];
        const formattedAmount = this.pos.format_currency_ref(amount);
        if (!amount) {
            return this.notification.add(
                this.env._t('Cash in/out of %s is ignored.', formattedAmount),
                { type: 'warning' }
            );
        }
        const extras = { formattedAmount, translatedType };
        await this.rpc({
            model: 'pos.session',
            method: 'try_cash_in_out_ref_currency',
            args: [[this.pos.pos_session.id], type, amount, reason, extras, currency_ref],
        });
        this.notification.add(
            this.env._t('Successfully made a cash %s of %s.', type, formattedAmount),
            { type: 'success' }
        );
    }
}
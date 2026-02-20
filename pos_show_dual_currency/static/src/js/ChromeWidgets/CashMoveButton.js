/** @odoo-module **/

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { CashMovePopupRefCurrency } from "../Popups/CashMovePopupRefCurrency";
import { sprintf } from "@web/core/utils/strings";

export class CashMoveButtonRefCurrency extends Component {
    static template = "CashMoveButtonRefCurrency";

    setup() {
        this.pos = usePos();
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    async onClickUSD() {
        const { confirmed, payload } = await this.popup.add(CashMovePopupRefCurrency);
        if (!confirmed) return;

        const { type, amount, reason, currency_ref } = payload;
        const translatedType = type === 'in' ? _t('in') : _t('out');
        const formattedAmount = this.pos.format_currency_ref(amount);

        if (!amount) {
            this.notification.add(
                sprintf(_t('Cash in/out of %s is ignored.'), formattedAmount),
                { type: 'danger' }
            );
            return;
        }

        const extras = { formattedAmount, translatedType };

        try {
            await this.orm.call(
                'pos.session',
                'try_cash_in_out_ref_currency',
                [[this.pos.pos_session.id], type, amount, reason, extras, currency_ref]
            );

             this.notification.add(
                sprintf(_t('Successfully made a cash %s of %s.'), type, formattedAmount),
                { type: 'success' }
            );
        } catch (error) {
             this.notification.add(
                _t('An error occurred during cash move.'),
                { type: 'danger' }
            );
            console.error(error);
        }
    }
}

Navbar.components = { ...Navbar.components, CashMoveButtonRefCurrency };

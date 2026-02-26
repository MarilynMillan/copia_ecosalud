/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { CashMovePopupRefCurrency } from "../Popups/CashMovePopup";

export class CashMoveButtonRefCurrency extends Component {
    static template = "pos_show_dual_currency.CashMoveButtonRefCurrency";

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
        const translatedType = type === 'in' ? _t("in") : _t("out");
        const formattedAmount = this.pos.format_currency_ref(amount);

        if (!amount) {
            return this.notification.add(
                _t("Cash in/out of %s is ignored.", formattedAmount),
                { type: "warning" }
            );
        }

        const extras = { formattedAmount, translatedType };

        await this.orm.call("pos.session", "try_cash_in_out_ref_currency", [
            [this.pos.pos_session.id],
            type,
            amount,
            reason,
            extras,
            currency_ref,
        ]);

        this.notification.add(
            _t("Successfully made a cash %s of %s.", type, formattedAmount),
            { type: "success" }
        );
    }
}

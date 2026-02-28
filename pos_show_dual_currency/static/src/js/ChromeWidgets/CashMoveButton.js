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
        // En Odoo 17, el popup service devuelve un objeto con { confirmed, payload }
        // Se espera que CashMovePopupRefCurrency esté implementado y registrado
        const { confirmed, payload } = await this.popup.add(CashMovePopupRefCurrency);
        if (!confirmed) return;

        // Asumimos que payload viene estructurado
        const { type, amount, reason, currency_ref } = payload;
        const translatedType = type === 'in' ? _t("in") : _t("out");

        // Formatear monto
        const formattedAmount = this.pos.format_currency_ref(amount);

        if (!amount) {
            return this.notification.add(
                _t("Cash in/out of %s is ignored.", formattedAmount),
                { type: "warning" }
            );
        }

        const extras = { formattedAmount, translatedType };

        try {
            await this.orm.call("pos.session", "try_cash_in_out_ref_currency", [
                this.pos.pos_session.id, // primer argumento debe ser ID (no lista de lista para record methods si llamamos al modelo?)
                // Espera: orm.call("model", "method", [ids, args...])
                // Si el método es 'try_cash_in_out_ref_currency' en pos.session:
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
        } catch (error) {
            console.error(error);
             this.notification.add(
                _t("Failed to make cash move."),
                { type: "danger" }
            );
        }
    }
}

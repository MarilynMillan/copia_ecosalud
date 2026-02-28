/** @odoo-module */

import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { Navbar } from "@point_of_sale/app/navbar/navbar"; // IMPORTANTE

const TRANSLATED_CASH_MOVE_TYPE = {
    in: _t("in"),
    out: _t("out"),
};


export class CashMoveButtonRefCurrency extends Component {
    static template = "pos_show_dual_currency.CashMoveButtonRefCurrency";

    setup() {
        this.pos = usePos();
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.popup = useService("popup"); // NUEVO: Servicio de popups en v17
    }

    async onClickUSD() {
        // CORRECCIÓN: En v17 se usa el servicio popup directamente
        const { confirmed, payload } = await this.popup.add("CashMovePopupRefCurrency");
        
        if (!confirmed) return;

        const { type, amount, reason, currency_ref } = payload;
        const translatedType = TRANSLATED_CASH_MOVE_TYPE[type];
        const formattedAmount = this.pos.format_currency_ref(amount);

        if (!amount) {
            return this.notification.add(
                _t("El movimiento de efectivo de %s fue ignorado.", formattedAmount),
                { type: "warning" }
            );
        }

        const extras = { formattedAmount, translatedType };

        try {
            await this.orm.call("pos.session", "try_cash_in_out_ref_currency", [
                [this.pos.pos_session.id],
                type,
                amount,
                reason,
                extras,
                currency_ref,
            ]);

            this.notification.add(
                _t("Se realizó con éxito una %s de %s.", translatedType, formattedAmount),
                { type: "success" }
            );
        } catch (error) {
            this.notification.add(_t("Error al registrar movimiento."), { type: "danger" });
        }
    }
}

// REGISTRO OBLIGATORIO: Para que el XML pueda usar el tag <CashMoveButtonRefCurrency />
Navbar.components = { ...Navbar.components, CashMoveButtonRefCurrency };
/** @odoo-module */

import { CashOpeningPopup } from "@point_of_sale/app/navbar/cash_opening_popup/cash_opening_popup";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(CashOpeningPopup.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");
        this.popup = useService("popup");

        // Extendemos el estado reactivo existente
        Object.assign(this.state, {
            openingCashUSD: this.pos.pos_session.cash_register_balance_start_mn_ref || 0,
            displayMoneyDetailsPopupUSD: false,
        });
    },

    async confirm() {
        // Sincronizamos localmente
        this.pos.pos_session.cash_register_balance_start_mn_ref = this.state.openingCashUSD;

        try {
            // Persistimos en el backend antes de cerrar
            await this.orm.call("pos.session", "set_cashbox_pos_usd", [
                [this.pos.pos_session.id],
                this.state.openingCashUSD,
                this.state.notes || "",
            ]);
        } catch (error) {
            console.error("Error al guardar el monto inicial en USD:", error);
            // Opcional: podrías mostrar un aviso aquí si es crítico
        }

        return super.confirm();
    }
});
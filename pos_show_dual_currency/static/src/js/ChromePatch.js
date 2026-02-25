/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { TRM } from "@pos_show_dual_currency/js/ChromeWidgets/TRM";
import { CashMoveButtonRefCurrency } from "@pos_show_dual_currency/js/ChromeWidgets/CashMoveButton";
import { patch } from "@web/core/utils/patch";

// Usamos Object.assign para asegurar que los nuevos componentes 
// se integren al objeto original de la Navbar
Object.assign(Navbar.components, { 
    TRM, 
    CashMoveButtonRefCurrency 
});

// También podemos usar el patch por si acaso otros módulos dependen de él
patch(Navbar.components, {
    TRM,
    CashMoveButtonRefCurrency
});
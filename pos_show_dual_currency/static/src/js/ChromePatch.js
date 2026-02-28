/** @odoo-module */
import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { TRM } from "./ChromeWidgets/TRM";
import { CashMoveButtonRefCurrency } from "./ChromeWidgets/CashMoveButton";

// Ensure components object exists (it usually does in Navbar)
if (!Navbar.components) {
    Navbar.components = {};
}

Object.assign(Navbar.components, { 
    TRM, 
    CashMoveButtonRefCurrency 
});

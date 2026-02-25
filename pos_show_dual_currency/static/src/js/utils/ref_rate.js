/** @odoo-module */

export function getRefRate(pos) {
    // Preferimos el rate calculado por sesión (backend), si existe
    const sessionRate = pos?.pos_session?.tax_today;
    if (sessionRate && sessionRate > 0) return sessionRate;

    const cfgRate = pos?.config?.show_currency_rate || 0;
    return cfgRate > 0 ? 1 / cfgRate : 1;
}

export function formatNoSymbolRef(pos, amount) {
    const cur = pos.res_currency_ref || pos.currency;
    return pos.format_currency_no_symbol(amount, cur.decimal_places, cur);
}
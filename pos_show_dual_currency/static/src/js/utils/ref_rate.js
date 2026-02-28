/** @odoo-module */

export function getRefRate(pos) {
    const sessionRate = pos?.pos_session?.tax_today;
    if (sessionRate && sessionRate > 0) return sessionRate;
    const cfgRate = pos?.config?.show_currency_rate || 0;
    return cfgRate > 0 ? (1 / cfgRate) : 1;
}

export function formatNoSymbolRef(pos, amount) {
    if (!pos) return amount;
    return pos.format_currency_ref(amount);
}
 
from odoo import models, fields, api, _

class SaleOrderDualCurrency(models.Model):
    _inherit = 'sale.order'

    company_currency_id = fields.Many2one(
        related='company_id.currency_id',
        string='Moneda de la Compañía',
        store=True,
        readonly=True
    )

    currency_id_dif = fields.Many2one('res.currency', string='Moneda Dual Ref.', default=lambda self: self.env.company.currency_id_dif)
    tax_today = fields.Float(string='Tasa Actual', store=True, digits='Dual_Currency_rate', 
                             default=lambda self: self.env.company.currency_id_dif.inverse_company_rate)
    
    # --- TOTALES REF USD (Solo Base, Impuesto, Total) ---
    amount_untaxed_usd = fields.Monetary(currency_field='currency_id_dif', string='Base Imponible Ref.', 
                                         compute='_compute_dual_currency_totals', store=True)
    amount_tax_usd = fields.Monetary(currency_field='currency_id_dif', string='Impuestos Ref.', 
                                     compute='_compute_dual_currency_totals', store=True)
    amount_total_usd = fields.Monetary(currency_field='currency_id_dif', string='Total Ref.', 
                                       compute='_compute_dual_currency_totals', store=True)

    # --- TOTALES REF VES (Solo Base, Impuesto, Total) ---
    amount_untaxed_ves = fields.Monetary(currency_field='company_currency_id', string='Base Imponible Bs.', 
                                         compute='_compute_dual_currency_totals', store=True)
    amount_tax_ves = fields.Monetary(currency_field='company_currency_id', string='Impuestos Bs.', 
                                     compute='_compute_dual_currency_totals', store=True)
    amount_total_ves = fields.Monetary(currency_field='company_currency_id', string='Total Bs.', 

                                       compute='_compute_dual_currency_totals', store=True)

    @api.onchange('currency_id')
    def _onchange_currency_id(self):
        if self.currency_id and self.currency_id_dif:
            self.tax_today = self.currency_id_dif.inverse_company_rate
        elif self.currency_id:
            self.tax_today = self.company_id.currency_id.inverse_company_rate 
        else:
            self.tax_today = 0.0

    @api.depends('amount_untaxed', 'amount_tax', 'amount_total', 'tax_today', 'currency_id', 'pricelist_id')
    def _compute_dual_currency_totals(self):
        for order in self:
            VES_Currency = order.company_id.currency_id
            
            rate = order.tax_today
            if not rate:
                rate = order.currency_id_dif.inverse_company_rate if order.currency_id_dif else 0.0
            
            # Reset
            order.amount_untaxed_usd = 0.0; order.amount_tax_usd = 0.0; order.amount_total_usd = 0.0
            order.amount_untaxed_ves = 0.0; order.amount_tax_ves = 0.0; order.amount_total_ves = 0.0

            if not rate or rate <= 0:
                continue

            def convert(amount, to_ves=True):
                return amount * rate if to_ves else amount / rate

            if order.currency_id != VES_Currency:
                # USD -> VES
                order.amount_untaxed_ves = convert(order.amount_untaxed, True)
                order.amount_tax_ves = convert(order.amount_tax, True)
                order.amount_total_ves = convert(order.amount_total, True)
            else: 
                # VES -> USD
                order.amount_untaxed_usd = convert(order.amount_untaxed, False)
                order.amount_tax_usd = convert(order.amount_tax, False)
                order.amount_total_usd = convert(order.amount_total, False)

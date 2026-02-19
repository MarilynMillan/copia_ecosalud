from odoo import models, fields, api

class AccountPaymentSeniat(models.Model):
    _inherit = 'account.payment'

    amount_bs_reference_custom = fields.Monetary(
        string='Importe Ref. (Bs)',
        currency_field='company_currency_id',
        compute='_compute_amount_bs_reference',
        store=True
    )
    
    igtf_bs_reference_custom = fields.Monetary(
        string='IGTF Ref. (Bs)',
        currency_field='company_currency_id',
        compute='_compute_amount_bs_reference',
        store=True
    )
    
    total_bs_reference_custom = fields.Monetary(
        string='Total Pagar Ref. (Bs)',
        currency_field='company_currency_id',
        compute='_compute_amount_bs_reference',
        store=True
    )

    @api.depends('amount', 'tax_today', 'currency_id', 'company_id', 'mount_igtf')
    def _compute_amount_bs_reference(self):
        for rec in self:
            rate = rec.tax_today if rec.tax_today else 1.0
            
            if rec.currency_id != rec.company_id.currency_id:
                rec.amount_bs_reference_custom = rec.amount * rate
                rec.igtf_bs_reference_custom = rec.mount_igtf * rate
            else:
                rec.amount_bs_reference_custom = rec.amount
                rec.igtf_bs_reference_custom = 0.0
            
            rec.total_bs_reference_custom = rec.amount_bs_reference_custom + rec.igtf_bs_reference_custom

    @api.onchange('journal_id', 'currency_id')
    def _onchange_force_igtf_seniat(self):
        for rec in self:
            if rec.currency_id and rec.company_id and rec.currency_id != rec.company_id.currency_id:
                rec.aplicar_igtf_divisa = True
                if rec.currency_id.name == 'USD':
                     rec.mount_igtf = rec.amount * rec.igtf_divisa_porcentage / 100
                     rec.amount_total_pagar = rec.mount_igtf + rec.amount
            else:
                rec.aplicar_igtf_divisa = False
                rec.mount_igtf = 0

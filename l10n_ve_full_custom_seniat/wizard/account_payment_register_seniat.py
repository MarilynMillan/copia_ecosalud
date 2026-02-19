from odoo import models, fields, api

class AccountPaymentRegisterSeniat(models.TransientModel):
    _inherit = 'account.payment.register'

    # --- Campos Nuevos para Referencia en Bs en el Wizard ---
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
        for wizard in self:
            rate = wizard.tax_today if wizard.tax_today else 1.0
            
            # Logica para calcular referencia
            if wizard.currency_id != wizard.company_id.currency_id:
                wizard.amount_bs_reference_custom = wizard.amount * rate
                wizard.igtf_bs_reference_custom = wizard.mount_igtf * rate
            else:
                wizard.amount_bs_reference_custom = wizard.amount
                wizard.igtf_bs_reference_custom = 0.0
            
            wizard.total_bs_reference_custom = wizard.amount_bs_reference_custom + wizard.igtf_bs_reference_custom

    @api.onchange('journal_id', 'currency_id')
    def _onchange_force_igtf_wizard(self):
        for wizard in self:
            if wizard.currency_id != wizard.company_id.currency_id:
                wizard.aplicar_igtf_divisa = True
                wizard._mount_igtf()
            else:
                wizard.aplicar_igtf_divisa = False
                wizard._mount_igtf()

    def _create_payments(self):
        payments = super(AccountPaymentRegisterSeniat, self)._create_payments()
        for payment in payments:
            # Transferir valores visuales al pago real si es necesario
            if payment.aplicar_igtf_divisa and payment.mount_igtf > 0:
                moves = payment.invoice_ids or payment.reconciled_invoice_ids
                for move in moves:
                    move._compute_igtf_aplicado() 
        return payments

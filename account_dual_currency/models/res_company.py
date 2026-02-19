# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command

class ResCompany(models.Model):
    _inherit = "res.company"

    currency_id_dif = fields.Many2one("res.currency",
                                      string="Moneda Dual Ref.",
                                      default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')],
                                                                                           limit=1), )

    return_actual_cost = fields.Boolean(string='Retornar Costo Actual', default=False)

    #asiento diferencial automatico
    automatic_diff_entry = fields.Boolean(string='Asiento Diferencial Automático', default=False)

    automatic_closing = fields.Boolean(string='Cierre de Factura Automático', default=False)
    closing_tolerance_usd = fields.Monetary(string='Tolerancia de Cierre $', default=0.0, currency_field='currency_id_dif')
    closing_tolerance_porc = fields.Float(string='Tolerancia de Cierre %', default=0.0)
    closing_journal_id = fields.Many2one('account.journal', string='Diario de Cierre', help='Diario donde se registrará el asiento de cierre')
    closing_account_id = fields.Many2one('account.account', string='Cuenta de Perdida')
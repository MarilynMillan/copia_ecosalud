# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    currency_id_dif = fields.Many2one("res.currency", related="company_id.currency_id_dif", string="Moneda Dual Ref.", readonly=False)

    return_actual_cost = fields.Boolean(related="company_id.return_actual_cost", string='Retornar Costo Actual', readonly=False)

    automatic_diff_entry = fields.Boolean(related="company_id.automatic_diff_entry", string='Asiento Diferencial Automático', readonly=False)
    automatic_closing = fields.Boolean(related="company_id.automatic_closing", string='Cierre de Factura Automático', readonly=False)
    closing_tolerance_usd = fields.Monetary(related="company_id.closing_tolerance_usd", string='Tolerancia de Cierre $', readonly=False)
    closing_tolerance_porc = fields.Float(related="company_id.closing_tolerance_porc", string='Tolerancia de Cierre %', readonly=False)
    closing_journal_id = fields.Many2one('account.journal', related="company_id.closing_journal_id", string='Diario de Cierre', readonly=False)
    closing_account_id = fields.Many2one('account.account', related="company_id.closing_account_id", string='Cuenta de Perdida', readonly=False)
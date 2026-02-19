# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models, Command
from odoo.osv import expression
from odoo.tools.misc import formatLang, frozendict

import markupsafe
import uuid

class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    currency_id_dif_statement = fields.Many2one("res.currency",
                                                string="Divisa de Referencia", related='wizard_id.currency_id_dif_statement')

    tasa_referencia_statement = fields.Float(string="Tasa", store=True, related='wizard_id.tasa_referencia_statement', digits='Dual_Currency_rate')

    balance_usd = fields.Monetary(
        currency_field='currency_id_dif_statement',
        compute='_compute_balance_usd',
        store=True,
        readonly=False,
    )
    debit_usd = fields.Monetary(
        currency_field='currency_id_dif_statement',
        compute='_compute_from_balance_usd',
    )
    credit_usd = fields.Monetary(
        currency_field='currency_id_dif_statement',
        compute='_compute_from_balance_usd',
    )

    source_balance_usd = fields.Monetary(currency_field='currency_id_dif_statement')
    source_debit_usd = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance_usd',
    )
    source_credit_usd = fields.Monetary(
        currency_field='company_currency_id',
        compute='_compute_from_source_balance_usd',
    )

    @api.depends('source_aml_id')
    def _compute_balance_usd(self):
        for line in self:
            if line.flag in ('aml', 'liquidity'):
                line.balance_usd = line.source_aml_id.balance_usd
            else:
                line.balance_usd = line.balance_usd

    @api.depends('balance_usd')
    def _compute_from_balance_usd(self):
        for line in self:
            line.debit_usd = line.balance_usd if line.balance_usd > 0.0 else 0.0
            line.credit_usd = -line.balance_usd if line.balance_usd < 0.0 else 0.0

    def _get_aml_values(self, **kwargs):
        vals = super(BankRecWidgetLine, self)._get_aml_values(**kwargs)
        vals['balance_usd'] = self.debit_usd - self.credit_usd
        return vals

    @api.depends('source_balance_usd')
    def _compute_from_source_balance_usd(self):
        for line in self:
            line.source_debit_usd = line.source_balance_usd if line.source_balance_usd > 0.0 else 0.0
            line.source_credit_usd = -line.source_balance_usd if line.source_balance_usd < 0.0 else 0.0
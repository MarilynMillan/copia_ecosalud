# -*- coding: utf-8 -*-

from odoo import models, fields, api, _

class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    tax_today = fields.Float(string="Tasa", default=lambda self: self._get_default_tasa(), digits='Dual_Currency_rate')
    currency_id_dif = fields.Many2one("res.currency",
        string="Divisa de Referencia",
        default=lambda self: self.env.company.currency_id_dif )
    currency_id_company = fields.Many2one("res.currency",
        string="Divisa compañia",
        default=lambda self: self.env.company.currency_id)

    def _get_default_tasa(self):
        return self.env.company.currency_id_dif.inverse_company_rate
# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class ResPartnerBank(models.Model):
    _inherit = ['res.partner.bank']
    _name = 'res.partner.bank'

    account_type = fields.Selection([
        ('checking', 'Corriente'),
        ('savings', 'Ahorro')
    ], string='Account type')

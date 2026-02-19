# -*- coding: utf-8 -*-

from odoo import models, fields,api

class HRRule(models.Model):
    _name = 'hr.salary.rule'
    _inherit = ['hr.salary.rule','analytic.mixin']

    origin_partner = fields.Selection(
        selection=[('empleado', 'Empleado'),
                   ('empresa', 'Empresa'),
                   ('otro', 'Otro Tercero')],
        string='Tipo de tercero', required=True, default="otro")

    partner_id = fields.Many2one('res.partner', 'Tercero')

    mostrar_cantidad = fields.Selection(
        selection=[('dias', 'Días'),
                     ('horas', 'Horas')], string='Mostrar cantidad')
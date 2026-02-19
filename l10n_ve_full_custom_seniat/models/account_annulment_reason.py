from odoo import models, fields

class AccountAnnulmentReason(models.Model):
    _name = 'account.annulment.reason'
    _description = 'Motivos de Corrección/Anulación'
    _order = 'sequence, id'

    name = fields.Char(string='Motivo', required=True)
    description = fields.Text(string='Descripción/Base Legal')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

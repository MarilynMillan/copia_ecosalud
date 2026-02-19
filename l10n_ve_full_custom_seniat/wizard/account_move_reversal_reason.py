from odoo import models, fields, api, _
from odoo.tools import Markup
from datetime import datetime

class AccountMoveResetWizard(models.TransientModel):
    _name = 'account.move.reset.wizard'
    _description = 'Justificación de Corrección Fiscal'

    reason_id = fields.Many2one('account.annulment.reason', string='Motivo Estándar', required=True)
    additional_notes = fields.Text(string='Detalles Adicionales', 
                                   help='Agregue detalles específicos (ej. Nro de RIF corregido)')
    move_id = fields.Many2one('account.move', string='Factura')

    def action_confirm_reset(self):
        self.ensure_one()
        move = self.move_id

        # 1. Obtener Fecha y Hora exacta en la Zona Horaria del Usuario
        # fields.Datetime.now() da la hora UTC, context_timestamp la convierte a VET
        now_user_tz = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        date_str = now_user_tz.strftime('%d/%m/%Y %I:%M:%S %p')

        # 2. Construir el mensaje con la nueva linea de tiempo
        message_content = (
            f'<ul>'
            f'<li>⚠️ <b>Documento restablecido a borrador para corrección.</b></li>'
            f'<li><b>Fecha de Ejecución:</b> {date_str}</li>'
            f'<li><b>Motivo Principal:</b> {self.reason_id.name}</li>'
            f'<li><b>Detalles/Notas:</b> {self.additional_notes or "N/A"}</li>'
            f'<li><b>Usuario Responsable:</b> {self.env.user.name}</li>'
            f'</ul>'
        )
        
        body = Markup(message_content)
        
        move.message_post(body=body, message_type='comment', subtype_xmlid='mail.mt_note')

        move.button_draft()
        
        return {'type': 'ir.actions.act_window_close'}

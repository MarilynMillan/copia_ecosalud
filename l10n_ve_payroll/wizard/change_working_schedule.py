# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import time
from base64 import b64encode, b64decode

class ChangeWorkingSchedule(models.TransientModel):
    _name = 'change.working.schedule'
    _description = 'Change Working Schedule'

    employee_ids = fields.Many2many('hr.employee', string='Employees')
    new_working_schedule = fields.Many2one('resource.calendar', string='Nuevo Horario de Trabajo')

    def change_working_schedule(self):
        for rec in self:
            if not rec.employee_ids:
                raise ValidationError(_('You must select an employee'))
            if not rec.new_working_schedule:
                raise ValidationError(_('You must select a new working schedule'))
            rec.employee_ids.contract_id.resource_calendar_id = rec.new_working_schedule.id
            rec.employee_ids.resource_calendar_id = rec.new_working_schedule.id
            rec.employee_ids.resource_calendar_id = rec.new_working_schedule.id

            #notificar ir.actions.client display_notification done
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Cambiado'),
                    'message': _('El horario de trabajo ha sido cambiado'),
                    'type': 'success',  # types: success, warning, danger, info
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

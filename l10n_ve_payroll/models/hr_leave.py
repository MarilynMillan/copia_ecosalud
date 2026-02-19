# -*- coding: utf-8 -*-

import pandas as pd
import os

from datetime import datetime, timedelta, time
from pytz import timezone, UTC
from odoo.tools import date_utils

from odoo import api, Command, fields, models, tools
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_compare, format_date
from odoo.tools.float_utils import float_round
from odoo.tools.misc import format_date
from odoo.tools.translate import _
from odoo.osv import expression
#os.environ['TZ'] = 'GTM-4'
class HrLeave(models.Model):
    _inherit = 'hr.leave'

    dias_habiles = fields.Integer(string="Días Hábiles", compute="_compute_dias_habiles", store=True)
    dias_fer_desc = fields.Integer(string="Días Feriados y Descanso", compute="_compute_dias_fer_desc", store=True)

    vaca_disponible = fields.Integer(string="Días Disponibles", compute="_compute_disponibles", store=True)
    dias_a_disfrutar = fields.Integer(string="Días a Disfrutar")

    is_vaca = fields.Boolean(string="Es Vacaciones", compute="_compute_is_vaca", store=True)

    @api.depends('request_date_from_period', 'request_hour_from', 'request_hour_to', 'request_date_from',
                 'request_date_to',
                 'request_unit_half', 'request_unit_hours', 'employee_id')
    def _compute_date_from_to(self):
        for holiday in self:
            if not holiday.request_date_from:
                holiday.date_from = False
            elif not holiday.request_unit_half and not holiday.request_unit_hours and not holiday.request_date_to:
                holiday.date_to = False
            else:
                #if (
                #        holiday.request_unit_half or holiday.request_unit_hours) and holiday.request_date_to != holiday.request_date_from:
                #    holiday.request_date_to = holiday.request_date_from

                day_period = {
                    'am': 'morning',
                    'pm': 'afternoon'
                }.get(holiday.request_date_from_period, None) if holiday.request_unit_half else None

                attendance_from, attendance_to = holiday._get_attendances(holiday.request_date_from,
                                                                          holiday.request_date_to,
                                                                          day_period=day_period)

                compensated_request_date_from = holiday.request_date_from
                compensated_request_date_to = holiday.request_date_to

                if holiday.request_unit_hours:
                    hour_from = holiday.request_hour_from
                    hour_to = holiday.request_hour_to
                else:
                    hour_from = attendance_from.hour_from
                    hour_to = attendance_to.hour_to

                holiday.date_from = self._to_utc(compensated_request_date_from, hour_from,
                                                 holiday.employee_id or holiday)
                holiday.date_to = self._to_utc(compensated_request_date_to, hour_to, holiday.employee_id or holiday)

    @api.depends('date_from', 'date_to', 'resource_calendar_id', 'holiday_status_id.request_unit','request_hour_from', 'request_hour_to')
    def _compute_duration(self):
        for holiday in self:
            holiday.date_from = holiday.date_from - timedelta(hours=4)
            holiday.date_to = holiday.date_to - timedelta(hours=4)

            if holiday.holiday_status_id.request_unit == 'hour':
                hours_from = float(holiday.request_hour_from)
                hours_to = float(holiday.request_hour_to)
                if hours_from < 0 or hours_to < 0:
                    raise ValidationError(_("Hours can't be negative"))
                holiday.number_of_hours = hours_to - hours_from
                #holiday.number_of_days = 1
            else:

                days, hours = holiday._get_duration()
                print(days, hours)
                holiday.number_of_hours = hours
                holiday.number_of_days = days


    @api.depends('holiday_status_id')
    def _compute_is_vaca(self):
        for rec in self:
            if rec.holiday_status_id.id == self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca').id:
                rec.is_vaca = True
            else:
                rec.is_vaca = False

    @api.onchange('dias_a_disfrutar')
    def _onchange_dias_a_disfrutar(self):
        for rec in self:
            if rec.holiday_status_id.id == self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca').id and rec.employee_id:
                if rec.dias_a_disfrutar > rec.vaca_disponible:
                    raise ValidationError(_("No puede solicitar más días de los disponibles"))
                fecha_desde = rec.request_date_from
                fecha_hasta = rec.request_date_from - timedelta(days=1)
                #recorrer dias_a_disfrutar para determinar la nueva fecha hasta
                if rec.dias_a_disfrutar > 0:
                    restasntes = rec.dias_a_disfrutar
                    while restasntes > 0:
                        fecha_hasta += timedelta(days=1)
                        if fecha_hasta.weekday() != 5 and fecha_hasta.weekday() != 6:
                            restasntes -= 1
                rec.request_date_to = fecha_hasta




    @api.depends('employee_id')
    def _compute_disponibles(self):
        for rec in self:
            if rec.employee_id:
                rec.vaca_disponible = rec.employee_id.contract_id.vaca_disponible
            else:
                rec.vaca_disponible = 0

    @api.depends('request_date_from', 'request_date_to')
    def _compute_dias_habiles(self):
        for rec in self:
            dh = 0
            dfd = 0
            a = pd.date_range(start=rec.request_date_from, end=rec.request_date_to)
            for i in a:
                if i.weekday() == 5 or i.weekday() == 6:
                    dfd += 1
                else:
                    dh += 1
            rec.dias_habiles = dh
            rec.dias_fer_desc = dfd

    def action_approve(self, check_state=True):
        self.date_from = self.date_from.replace(hour=0, minute=0, second=0)
        #self.date_to = self.date_to.replace(hour=23, minute=59, second=59)
        creados = []
        for rec in self:
            if rec.holiday_type == 'employee' and rec.holiday_status_id.id == self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca').id:
                #contiene fin de semana
                contiene_fin_semana = False
                a = pd.date_range(start=rec.request_date_from, end=rec.request_date_to)
                for i in a:
                    if i.weekday() == 5 or i.weekday() == 6:
                        contiene_fin_semana = True


                #verifica si holiday_status_id es igual a ref l10n_ve_payroll.holiday_status_ve_vaca
                if rec.holiday_status_id.id == self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca').id and contiene_fin_semana:
                    #crear un ciclo entre las fechas request_date_from y request_date_to y verifica si tienen sabado y domingo
                    #si tienen sabado y domingo entonces no se puede confirmar
                    #si no tienen sabado y domingo entonces se puede confirmar
                    fecha_inicio = rec.date_from
                    fecha_fin = rec.date_to
                    periodos = []
                    periodo_num = 0
                    x = 0
                    original_modificado = False
                    a = pd.date_range(start=fecha_inicio, end=fecha_fin)
                    for i in a:
                        if i.weekday() == 5 or i.weekday() == 6:
                            if x > 0 and not original_modificado:
                                rec.request_date_to = i - timedelta(days=1)
                                original_modificado = True
                                #commit
                                #self.env.cr.commit()
                            # si ya hay periodos, cerrar la fecha del ultimo periodo
                            if periodos and original_modificado and i.weekday() == 5:
                                periodo_num += 1
                                periodos.append([periodo_num, i - timedelta(days=5), i - timedelta(days=1)])

                            #si es sabado y es el ultimo día en a, crear el periodo request_date_from y request_date_to con la misma fecha
                            if i == a[-1] and i.weekday() == 5:
                                periodo_num += 1
                                periodos.append([periodo_num, i, i])

                            #si es domingo se crea el periodo request_date_from y request_date_to con i y un día anterior
                            if i.weekday() == 6:
                                periodo_num += 1
                                periodos.append([periodo_num, i - timedelta(days=1), i])
                        #si i es la ultima fecha en a y no es sabado ni domingo, crear el periodo request_date_from y request_date_to con la misma fecha
                        if i == a[-1] and i.weekday() != 5 and i.weekday() != 6:
                            periodo_num += 1
                            periodos.append([periodo_num, i - timedelta(days=i.weekday()), i])

                        x += 1
                    #por cada uno de los periodos, crear un nuevo registro de hr.leave con holiday_status_id == self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca_des_fer').id
                    for periodo in periodos:
                        #agregar horas a periodo
                        periodo[1] = periodo[1].replace(hour=rec.date_from.hour, minute=rec.date_from.minute, second=rec.date_from.second)
                        periodo[2] = periodo[2].replace(hour=rec.date_to.hour, minute=rec.date_to.minute, second=rec.date_to.second)

                        if periodo[1] == rec.request_date_from:
                            rec.request_date_to = periodo[2]
                            if periodo[1].weekday() == 5 or periodo[1].weekday() == 6:
                                rec.holiday_status_id = self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca_des_fer').id
                        else:
                            #number_of_days from periodo[1] to periodo[2]
                            number_of_days = (periodo[2] - periodo[1]).days + 2
                            data = {
                                'name': rec.display_name or '',
                                'state': 'confirm',
                                'user_id': rec.user_id.id or self.env.uid,
                                'employee_id': rec.employee_id.id,
                                'holiday_type': rec.holiday_type,
                                'employee_ids': rec.employee_ids.ids,
                                'date_from': periodo[1],
                                'date_to': periodo[2],
                                'request_date_from': periodo[1].strftime('%Y-%m-%d'),
                                'request_date_to': periodo[2].strftime('%Y-%m-%d'),
                                'number_of_days': number_of_days,
                                'tz': rec.tz
                            }

                            #si periodo[1] .weekday() == 5 or .weekday() == 6 crear con holiday_status_ve_vaca_des_fer
                            if periodo[1].weekday() == 5 or periodo[1].weekday() == 6:
                                data['holiday_status_id'] = self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca_des_fer').id
                            else:
                                data['holiday_status_id'] = self.env.ref('l10n_ve_payroll.holiday_status_ve_vaca').id

                            print(data)
                            #crear y confirmar
                            nuevo = self.env['hr.leave'].with_user(rec.employee_id).create(data)
                            nuevo._compute_number_of_days()
                            nuevo._compute_display_name()
                            nuevo._compute_tz()
                            #nuevo.action_confirm()
                            creados.append(nuevo)


        res = super(HrLeave, self).action_approve()
        if creados:
            for nuevo in creados:
                nuevo.with_user(rec.employee_id).action_approve()
        for holiday in self:
            if holiday.holiday_status_id.work_entry_type_id.id == self.env.ref('l10n_ve_payroll.work_entry_type_HED').id:
                #eliminar resource.calendar.leaves con el mismo holiday_id
                self.env['resource.calendar.leaves'].search([('holiday_id', '=', holiday.id)]).unlink()
            if holiday.holiday_status_id.work_entry_type_id.id == self.env.ref('l10n_ve_payroll.work_entry_type_HEN').id:
                #eliminar resource.calendar.leaves con el mismo holiday_id
                self.env['resource.calendar.leaves'].search([('holiday_id', '=', holiday.id)]).unlink()
        return res

    def name_get(self):
        res = []
        for leave in self:
            user_tz = timezone(leave.tz)
            date_from_utc = leave.date_from #and leave.date_from.astimezone(user_tz).date()
            date_to_utc = leave.date_to #and leave.date_to.astimezone(user_tz).date()
            if self.env.context.get('short_name'):
                if leave.leave_type_request_unit == 'hour':
                    res.append((leave.id, _("%s : %.2f hours") % (leave.name or leave.holiday_status_id.name, leave.number_of_hours_display)))
                else:
                    res.append((leave.id, _("%s : %.2f days") % (leave.name or leave.holiday_status_id.name, leave.number_of_days)))
            else:
                if leave.holiday_type == 'company':
                    target = leave.mode_company_id.name
                elif leave.holiday_type == 'department':
                    target = leave.department_id.name
                elif leave.holiday_type == 'category':
                    target = leave.category_id.name
                elif leave.employee_id:
                    target = leave.employee_id.name
                else:
                    target = ', '.join(leave.employee_ids.mapped('name'))
                display_date = format_date(self.env, date_from_utc) or ""
                if leave.leave_type_request_unit == 'hour':
                    if self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f hours on %(date)s",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_hours_display,
                                date=display_date,
                            )
                        ))
                    else:
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f hours on %(date)s",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_hours_display,
                                date=display_date,
                            )
                        ))
                else:
                    if leave.number_of_days > 1 and date_from_utc and date_to_utc:
                        display_date += ' / %s' % format_date(self.env, date_to_utc) or ""
                    if not target or self.env.context.get('hide_employee_name') and 'employee_id' in self.env.context.get('group_by', []):
                        res.append((
                            leave.id,
                            _("%(leave_type)s: %(duration).2f days (%(start)s)",
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_days,
                                start=display_date,
                            )
                        ))
                    else:
                        res.append((
                            leave.id,
                            _("%(person)s on %(leave_type)s: %(duration).2f days (%(start)s)",
                                person=target,
                                leave_type=leave.holiday_status_id.name,
                                duration=leave.number_of_days,
                                start=display_date,
                            )
                        ))
        return res

    @api.model_create_multi
    def create(self, vals_list):
        to_remove = []
        for vals in vals_list:
            #verificar si viene parent_id
            if 'parent_id' in vals:
                #si viene parent_id, buscar el parent_id y verificar si es de tipo vacaciones
                parent = self.env['hr.leave'].browse(vals['parent_id'])
                if parent.holiday_status_id.work_entry_type_id.id == self.env.ref('l10n_ve_payroll.work_entry_type_HED').id:
                    #eliminar de la lista vals_list
                    to_remove.append(vals)
                if parent.holiday_status_id.work_entry_type_id.id == self.env.ref('l10n_ve_payroll.work_entry_type_HEN').id:
                    #eliminar de la lista vals_list
                    to_remove.append(vals)
        for vals in to_remove:
            vals_list.remove(vals)
        holidays = super(HrLeave, self).create(vals_list)

        return holidays

    def _get_leaves_on_public_holiday(self):
        return False
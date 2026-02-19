# -*- coding: utf-8 -*-
from odoo import api, Command, fields, models, tools
import itertools
from datetime import datetime, timedelta, time

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    #reemplazar el metodo create
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('work_entry_type_id', False):
                if vals['work_entry_type_id'] == self.env.ref('l10n_ve_payroll.work_entry_type_VACA').id:
                    #si la fecha es fin de semana se le cambia el tipo de entrada
                    if fields.Date.from_string(vals.get('date_start')).weekday() in [5,6]:
                        vals['work_entry_type_id'] = self.env.ref('l10n_ve_payroll.work_entry_type_VACA_des_fer').id
                if not vals['work_entry_type_id'] == self.env.ref('l10n_ve_payroll.work_entry_type_HED').id:
                    if vals.get('date_start', False):
                        #aumentar 1 hora  a la fecha de inicio + timedelta 1 hora
                        date_start = fields.Datetime.from_string(vals['date_start'])
                        vals['date_start'] = date_start + timedelta(hours=1)
                    if vals.get('date_stop', False):
                        #aumentar 1 hora  a la fecha de fin
                        date_stop = fields.Datetime.from_string(vals['date_stop'])
                        vals['date_stop'] = date_stop + timedelta(hours=1)
        return super(HrWorkEntry, self).create(vals_list)

    def _mark_conflicting_work_entries(self, start, stop):
        """
        Set `state` to `conflict` for overlapping work entries
        between two dates.
        If `self.ids` is truthy then check conflicts with the corresponding work entries.
        Return True if overlapping work entries were detected.
        """
        # Use the postgresql range type `tsrange` which is a range of timestamp
        # It supports the intersection operator (&&) useful to detect overlap.
        # use '()' to exlude the lower and upper bounds of the range.
        # Filter on date_start and date_stop (both indexed) in the EXISTS clause to
        # limit the resulting set size and fasten the query.
        self.flush_model(['date_start', 'date_stop', 'employee_id', 'active','work_entry_type_id'])
        query = """
            SELECT b1.id,
                   b2.id
              FROM hr_work_entry b1
              JOIN hr_work_entry b2
                ON b1.employee_id = b2.employee_id
               AND b1.id <> b2.id
               AND b1.work_entry_type_id = b2.work_entry_type_id
             WHERE b1.date_start <= %(stop)s
               AND b1.date_stop >= %(start)s
               AND b1.active = TRUE
               AND b2.active = TRUE
               AND tsrange(b1.date_start, b1.date_stop, '()') && tsrange(b2.date_start, b2.date_stop, '()')
               AND {}
        """.format("b2.id IN %(ids)s" if self.ids else "b2.date_start <= %(stop)s AND b2.date_stop >= %(start)s")
        self.env.cr.execute(query, {"stop": stop, "start": start, "ids": tuple(self.ids)})
        conflicts = set(itertools.chain.from_iterable(self.env.cr.fetchall()))
        self.browse(conflicts).write({
            'state': 'conflict',
        })
        return bool(conflicts)
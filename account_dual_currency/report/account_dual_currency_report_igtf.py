# -*- coding: utf-8 -*-

from odoo import models, api, fields, _
from odoo.tools.misc import formatLang, format_date, xlsxwriter
from odoo.tools import config, date_utils, get_lang, float_compare, float_is_zero
import datetime
import pandas as pd
import locale
#locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
class VenezuelaReportCustomHandlerIGTF(models.AbstractModel):
    _name = 'account_dual_currency.report.handler.igtf'
    _inherit = 'account.report.custom.handler'
    _description = 'Venezuela IGTF Report Custom Handler'

    @api.model
    def is_zero(self, amount, currency=False, figure_type=None, digits=1):
        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            return currency.is_zero(amount)

        if figure_type == 'integer':
            digits = 0
        return float_is_zero(amount, precision_digits=digits)

    @api.model
    def format_value(self, value, currency=False, blank_if_zero=True, figure_type=None, digits=2):
        """ Formats a value for display in a report (not especially numerical). figure_type provides the type of formatting we want.
        """
        if figure_type == 'none':
            return value

        if value is None:
            return ''

        if figure_type == 'monetary':
            currency = currency or self.env.company.currency_id
            if self._context.get('currency_dif'):
                if self._context.get('currency_dif') == self._context.get('currency_id_company_name'):
                    currency = self.env.company.currency_id
                else:
                    currency = self.env.company.currency_id_dif
            digits = None
        elif figure_type in ('date', 'datetime'):
            return format_date(self.env, value)
        else:
            currency = None

        if self.is_zero(value, currency=currency, figure_type=figure_type, digits=digits):
            if blank_if_zero:
                return ''
            # don't print -0.0 in reports
            value = abs(value)

        if self._context.get('no_format'):
            return value

        formatted_amount = formatLang(self.env, value, currency_obj=currency, digits=digits)

        if figure_type == 'percentage':
            return f"{formatted_amount}%"

        return formatted_amount


    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if 'date' in options:
            date_from = options['date']['date_from']
            date_to = options['date']['date_to']
            options['date']['string'] = 'Desde %s - Hasta %s' % (
                datetime.datetime.strptime(date_from, "%Y-%m-%d").strftime("%d/%m/%Y"),
                datetime.datetime.strptime(date_to, "%Y-%m-%d").strftime("%d/%m/%Y"))
            options['column_headers'] = [
                [{'name': options['date']['string'],
                  'forced_options': {
                      'date': options['date'],
                  }
                  }],
            ]

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        # options['column_headers'] = [
        #     [{'name': options['date']['string'],
        #       'forced_options': {
        #           'date': options['date'],
        #       }
        #       }],
        # ]
        date_from = options['date']['date_from']
        date_to = options['date']['date_to']
        options['date']['string'] = 'Desde %s - Hasta %s' % (
        datetime.datetime.strptime(date_from, "%Y-%m-%d").strftime("%d/%m/%Y"),
        datetime.datetime.strptime(date_to, "%Y-%m-%d").strftime("%d/%m/%Y"))
        lines = []
        company_id = self.env.context.get('company_id') or self.env.company.id
        company_id = self.env['res.company'].browse(company_id)
        currency_company = company_id.currency_id
        currency_dif = company_id.currency_id_dif
        dominio = [('move_type', 'in', ['out_invoice', 'out_refund']),
                   ('company_id', '=', company_id.id), ('state', '=', 'posted'), ('invoice_date', '>=', date_from), ('invoice_date', '<=', date_to),('igtf_aplicado','>',0)]
        doc_igtf_ids = self.env['account.move'].search(dominio, order='invoice_date asc')

        if not doc_igtf_ids:
            #crear una linea con el mensaje de que no hay datos
            columns_total = [{'name': '', 'class': 'text'} for i in range(11)]
            lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total', parent_line_id=None),
                'name': 'No hay IGTF aplicado en el periodo seleccionado',
                'level': 0,
                'unfoldable': False,
                'unfolded': False,
                'expand_function': None,
                'columns': columns_total,
            }))
        else:
            igtf_aplicado_sum = 0
            amount_total_sum = 0
            amount_total_usd_sum = 0
            igtf_base_sum = 0
            igtf_base_divisa_sum = 0
            id = 1
            for line in doc_igtf_ids:
                fecha = line.invoice_date.strftime('%d-%m-%Y')
                igtf_aplicado = line.igtf_aplicado * line.tax_today
                igtf_aplicado_sum += igtf_aplicado
                amount_total = line.amount_total if line.currency_id == currency_company else line.amount_total * line.tax_today
                amount_total_sum += amount_total
                amount_total_usd_sum += line.amount_total_usd
                igtf_base = line.igtf_base * line.tax_today
                igtf_base_sum += igtf_base
                igtf_base_divisa = line.igtf_base
                igtf_base_divisa_sum += igtf_base_divisa
                columns = [{'name': line.name, 'class': 'text'},
                           {'name': line.nro_ctrl, 'class': 'text'},
                           {'name': str(fecha), 'class': 'text'},
                           {'name': line.partner_id.name, 'class': 'text'},
                           {'name': line.partner_id.rif, 'class': 'text'},
                           {'name': self.format_value(amount_total, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                           {'name': self.format_value(igtf_base, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                           {'name': '$ %s' % self.format_value(igtf_base_divisa, currency=currency_dif, blank_if_zero=True, figure_type='string'), 'class': 'numeric text-end'},
                           {'name': str(line.tax_today), 'class': 'text'},
                           {'name': self.format_value(igtf_aplicado, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                           ]
                line_id = report._get_generic_line_id('account.move', line.id)
                lines.append((id, {
                    'id': line_id,
                    'name': '%s' % id,
                    'level': 3,
                    'unfoldable': False,
                    'unfolded': False,
                    'expand_function': None,
                    'columns': columns,
                }))
                id += 1

            columns_total = [{'name': '%s OPE.' % (id - 1), 'class': 'text'},
                             {'name': '', 'class': 'text'},
                                {'name': '', 'class': 'text'},
                                {'name': '', 'class': 'text'},
                                {'name': '', 'class': 'text'},
                                {'name': self.format_value(amount_total_sum, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                                {'name': self.format_value(igtf_base_sum, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                                {'name': '$ %s' % self.format_value(amount_total_usd_sum, currency=currency_dif, blank_if_zero=True, figure_type='string'), 'class': 'numeric text-end'},
                                {'name': '', 'class': 'text'},
                                {'name': self.format_value(igtf_aplicado_sum, currency=currency_company, blank_if_zero=True, figure_type='monetary'), 'class': 'numeric text-end'},
                             ]
            lines.append((0, {
                'id': report._get_generic_line_id(None, None, markup='total', parent_line_id=None),
                'name': 'Total',
                'level': 0,
                'unfoldable': False,
                'unfolded': False,
                'expand_function': None,
                'columns': columns_total,
            }))

        #buscar


        return lines




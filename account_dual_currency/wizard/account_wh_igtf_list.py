# -*- coding: utf-8 -*-

import base64
import locale
import xlwt
from datetime import date, datetime
from io import BytesIO

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class RetentionIGTF(models.Model):
    _name = 'account.wh.igtf.list'
    _description = 'Listado Retención IGTF'

    company = fields.Many2one('res.company', required=True, default=lambda self: self.env.company, readonly=True,
                              store=True)
    start_date = fields.Date(required=True, default=fields.Datetime.now)
    end_date = fields.Date(required=True, default=fields.Datetime.now)
    supplier = fields.Boolean(default=False, string='Facturas de Proveedor')
    customer = fields.Boolean(default=True, string='Facturas de Cliente')
    partner_id = fields.Many2one('res.partner')

    state = fields.Selection([('choose', 'choose'), ('get', 'get')], default='choose')
    report = fields.Binary('Descargar xls', filters='.xls', readonly=True)
    name = fields.Char('File Name', size=32)

    def generate_retention_igtf_pdf(self):
        b = []
        name = []
        data = {
            'ids': self.ids,
            'model': 'report.account_dual_currency.report_retention_igtf',
            'form': {
                'date_start': self.start_date,
                'date_stop': self.end_date,
                'company': self.company.id,
                'supplier': self.supplier,
                'partner_id': self.partner_id.id,
                'customer': self.customer,
            },
        }
        return self.env.ref('account_dual_currency.action_report_retention_igtf').report_action(self, data=data)

    @staticmethod
    def separador_cifra(valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto


class ReportRetentionIGTF(models.AbstractModel):
    _name = 'report.account_dual_currency.report_retention_igtf_list'

    @api.model
    def _get_report_values(self, docids, data=None):
        date_start = data['form']['date_start']
        end_date = data['form']['date_stop']
        company_id = data['form']['company']
        today = date.today()
        supplier = data['form']['supplier']
        customer = data['form']['customer']
        dominio = [('company_id', '=', company_id), ('state', '=', 'posted'), ('invoice_date', '>=', date_start),
                   ('invoice_date', '<=', end_date)]
        if supplier and not customer:
            dominio.append(('move_type', 'in', ['in_invoice', 'in_refund']))
        elif not supplier and customer:
            dominio.append(('move_type', 'in', ['out_invoice', 'out_refund']))
        elif supplier and customer:
            dominio.append(('move_type', 'in', ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']))


        company = self.env['res.company'].search([('id', '=', company_id)])

        doc_igtf_ids = self.env['account.move'].search(dominio, order='invoice_date asc')

        if not doc_igtf_ids:
            raise UserError('No hay IGTF aplicado y el periodo seleccionado')

        docs = []
        total_amount = 0
        o = doc_igtf_ids[0]
        for line in doc_igtf_ids.filtered(lambda x: x.igtf_aplicado > 0):
            fecha_factura = line.invoice_date
            fecha_inicio = fecha_factura.strftime('%d-%m-%Y')
            total_amount += line.igtf_aplicado
            documento = ''
            if line.partner_id.company_type == 'person':
                if line.partner_id.rif:
                    documento = line.partner_id.rif
                elif line.partner_id.nationality == 'V' or line.partner_id.nationality == 'E':
                    documento = str(line.partner_id.nationality) + str(line.partner_id.identification_id)
                else:
                    documento = str(line.partner_id.identification_id)
            else:
                documento = line.partner_id.rif

            docs.append({
                'fecha': fecha_inicio,
                'documento': line.name,
                'proveedor': line.partner_id.name,
                'rif': documento,
                'factura': line.supplier_invoice_number,
                'control': line.nro_ctrl,
                'monto_suj_retencion': self.separador_cifra(line.amount_untaxed),
                'tasa_porc': 3.0,
                'impuesto_retenido': self.separador_cifra(line.igtf_aplicado),
            })

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'end_date': end_date,
            'start_date': date_start,
            'today': today,
            'company': company,
            'company_id': company,
            'o': o,
            'docs': docs,
            'total_amount': self.separador_cifra(total_amount)
        }


    @staticmethod
    def separador_cifra(valor):
        monto = '{0:,.2f}'.format(valor).replace('.', '-')
        monto = monto.replace(',', '.')
        monto = monto.replace('-', ',')
        return monto

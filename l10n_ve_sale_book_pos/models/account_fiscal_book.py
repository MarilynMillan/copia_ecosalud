# coding: utf-8
from email.policy import default

from odoo import fields, models

class AccountFiscalBook(models.Model):
    _inherit = 'account.fiscal.book'
    _description = "Libro de Compra Incluyendo POS"

    pos_order_ids = fields.Many2many('pos.order', string='Ordenes POS')

    pos_report_z_ids = fields.Many2many('pos.report.z', string='Reportes Z')

    pos_group = fields.Boolean(string='Agrupar por POS', default=True)

    def update_book(self):
        super(AccountFiscalBook, self).update_book()
        for rec in self:
            if rec.type == 'sale':
                self._update_pos_book()

    def _update_pos_book(self):
        self.ensure_one()
        local_period = self.get_time_period(self.time_period)
        print('local_period', local_period)
        pos_report_z = self.env['pos.report.z'].search([
            ('date', '>=', local_period.get('dt_from')),
            ('date', '<=', local_period.get('dt_to')),
            ('state', '=', 'done'),('company_id', '=', self.company_id.id)])
        self.pos_report_z_ids = pos_report_z if pos_report_z else False
        self.pos_order_ids = pos_report_z.mapped('pos_order_ids')
        self.process_pos_order()

    def process_pos_order(self):
        for rec in self:
            total_sin_iva_general = 0
            total_sin_iva_exento = 0
            total_iva = 0
            z_ids_group = []
            z_ids_group_nc = []
            pos_z_report_number = ''
            total_sin_iva_general_group = 0
            total_sin_iva_exento_group = 0
            total_iva_group = 0
            date_order_group = ''
            session_move_id_group_date = ''
            serial_number_group = ''
            for z in rec.pos_report_z_ids:
                total_sin_iva_general = z.total_base_iva_16
                total_sin_iva_exento = z.total_exempt
                total_iva = z.total_iva_16

                total_sin_iva_general_nc = z.total_base_iva_16_nc
                total_sin_iva_exento_nc = z.total_exempt_nc
                total_iva_nc = z.total_iva_16_nc
                print('total_sin_iva_general_nc', total_sin_iva_general_nc)
                print('total_sin_iva_exento_nc', total_sin_iva_exento_nc)
                print('total_iva_nc', total_iva_nc)

                total_sin_iva_general_group += total_sin_iva_general
                total_sin_iva_exento_group += total_sin_iva_exento
                total_iva_group += total_iva

                z_ids_group.append({'fb_id': rec.id,
                                      'type': 'tp',
                                      'pos_z_id': z.id,
                                      'invoice_id': False,
                                      'doc_type': 'FACT',
                                      'emission_date': z.date,
                                      'accounting_date': z.date,
                                      'fac_desde': z.fac_desde,
                                      'fac_hasta': z.fac_hasta,
                                      'invoice_number': '',
                                      'partner_name': '',
                                      'partner_vat': '',
                                      'people_type': 'pnre',
                                      'void_form': '01-REG',
                                      'total_with_iva': total_sin_iva_general + total_sin_iva_exento + total_iva,
                                      'vat_exempt': total_sin_iva_exento,
                                      'vat_general_base': total_sin_iva_general,
                                      'vat_general_tax': total_iva,
                                      'fiscal_printer': z.x_fiscal_printer_code,
                                      'z_report': z.number})
                if (total_sin_iva_general_nc + total_sin_iva_exento_nc + total_iva_nc) > 0:
                    z_ids_group_nc.append({'fb_id': rec.id,
                                            'type': 'tp',
                                            'pos_z_id': z.id,
                                            'invoice_id': False,
                                            'doc_type': 'N/CR',
                                            'emission_date': z.date,
                                            'accounting_date': z.date,
                                            'fac_desde': z.nc_desde,
                                            'fac_hasta': z.nc_hasta,
                                            'invoice_number': '',
                                            'partner_name': '',
                                            'partner_vat': '',
                                            'people_type': 'pnre',
                                            'void_form': '01-REG',
                                            'total_with_iva': total_sin_iva_general_nc + total_sin_iva_exento_nc + total_iva_nc,
                                            'vat_exempt': total_sin_iva_exento_nc,
                                            'vat_general_base': total_sin_iva_general_nc,
                                            'vat_general_tax': total_iva_nc,
                                            'fiscal_printer': z.x_fiscal_printer_code,
                                            'z_report': z.number})

            rec.fbl_ids.create(z_ids_group)
            if z_ids_group_nc:
                rec.fbl_ids.create(z_ids_group_nc)
            self.order_book_lines(rec.id)

            #modifica el resumen del libro
            linea_resumen_general = rec.fbts_ids.filtered(lambda l: l.op_type == 'tp' and l.tax_type == 'general')
            if linea_resumen_general:
                linea_resumen_general.base_amount_sum += total_sin_iva_general_group
                linea_resumen_general.tax_amount_sum += total_iva_group

            linea_resumen_exento = rec.fbts_ids.filtered(lambda l: l.op_type == 'tp' and l.tax_type == 'exento')
            if linea_resumen_exento:
                linea_resumen_exento.base_amount_sum += total_sin_iva_exento_group

            rec.base_amount += (total_sin_iva_general_group + total_sin_iva_exento_group)
            rec.tax_amount += total_iva_group

    def clear_book(self):
        super(AccountFiscalBook, self).clear_book()
        self.pos_order_ids = False

class AccountFiscalBookLines(models.Model):
    _inherit = 'account.fiscal.book.line'

    pos_z_id = fields.Many2one('pos.report.z', string='Reporte Z')

    fac_desde = fields.Char(string='Factura Desde')
    fac_hasta = fields.Char(string='Factura Hasta')

# coding: utf-8
##############################################################################

###############################################################################
import time
import base64
import xlsxwriter
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, date, timedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from io import BytesIO


class FiscalBookWizard(models.TransientModel):
    """
    Sales book wizard implemented using the osv_memory wizard system
    """
    _inherit = "account.fiscal.book.wizard"

    def check_report_xlsx(self):
        if self.type == 'purchase':
            file_name = 'Libro_Compra.xlsx'
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_numbers': False})
            sheet = workbook.add_worksheet('Libro Compra')
            formats = self.set_formats(workbook)
            datos_compras, datos_compras_ajustes = self.get_datas_compras()
            if not datos_compras:
                raise UserError('No hay datos disponibles')
            sheet.merge_range('B3:G3', datos_compras[0]['company_name'], formats['string_titulo'])
            sheet.merge_range('M3:T3', 'Libro de Compras', formats['string_titulo'])
            sheet.merge_range('B4:G4', datos_compras[0]['company_rif'], formats['string'])
            format_new = "%d/%m/%Y"
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT).date()
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT).date()

            sheet.merge_range('M4:N4', 'Desde', formats['string'])
            sheet.merge_range('O4:P4', '%s' % date_start.strftime(format_new), formats['date'])
            sheet.merge_range('Q4:R4', 'Hasta', formats['string'])
            sheet.merge_range('S4:T4', '%s' % date_end.strftime(format_new), formats['date'])

            sheet.set_row(5, 30)
            sheet.merge_range('N6:W6', 'Compras Internas', formats['title'])
            sheet.merge_range('X6:AB6', 'Compras de Importaciones', formats['title'])
            sheet.merge_range('AC6:AD6', 'Retención IVA Proveedores', formats['title'])

            row = 6
            col = 1
            titles = [(1, 'Nro. Op'), (2, 'Fecha Emisión Doc.'), (3, 'Nro. de RIF'), (4, 'Nombre ó Razón Social'),
                      (5, 'Tipo Prov.'),
                      (6, 'Nro. de Factura'), (7, 'Nro. de Control'), (8, 'Nro. Nota de Crédito'),
                      (9, 'Nro. Nota de Débito'),
                      (10, 'Tipo de Trans'), (11, 'Nro. Factura Afectada'), (12, 'Total Compras con IVA'),
                      (13, 'Compras sin Derecho a Crédito'),
                      (14, 'Base Imponible Alicuota General'),
                      (15, '% Alicuota General'), (16, 'Impuesto (I.V.A) Alicuota General'),
                      (17, 'Base Imponible Alicuota Reducida'),
                      (18, '% Alicuota Reducida'), (19, 'Impuesto (I.V.A) Alicuota Reducida'),
                      (20, 'Base Imponible Alicuota Adicional'),
                      (21, '% Alicuota Adicional'), (22, 'Impuesto (I.V.A) Alicuota Adicional'),
                      (23, 'Base Imponible Alicuota General'),
                      (24, '% Alicuota General'), (25, 'Impuesto (I.V.A) Alicuota General'),
                      (26, 'Nro. Planilla Importación'),
                      (27, 'Nro. Expediente Importación'),
                      (28, 'Nro. de Comprobante'), (29, 'IVA Ret (Vend.)')]

            # sheet.set_row(6, cell_format=formats['title'])
            for title in titles:
                sheet.write(row, col, title[1], formats['title'])
                col += 1
            row += 1
            col = 1

            contador_datos_compras = 1
            row_suma_ini = row
            for d in datos_compras:
                col = 1
                sheet.write(row, col, contador_datos_compras)
                col += 1
                sheet.write(row, col, d['emission_date'])
                col += 1
                sheet.write(row, col, d['partner_vat'])
                col += 1
                sheet.write(row, col, d['partner_name'])
                col += 1
                sheet.write(row, col, d['people_type'])
                col += 1
                sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['ctrl_number'], formats['string'])
                col += 1
                sheet.write(row, col, d['credit_affected'] if d['doc_type'] == 'N/CR' else '', formats['string'])
                col += 1
                sheet.write(row, col, d['debit_affected'] if d['debit_affected'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['type'])
                col += 1
                sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '', formats['string'])
                col += 1
                sheet.write(row, col, d['total_with_iva'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_exempt'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax_importaciones'], formats['number'])
                col += 1
                sheet.write(row, col, d['nro_planilla'], formats['string'])
                col += 1
                sheet.write(row, col, d['nro_expediente'], formats['string'])
                col += 1
                sheet.write(row, col, str(d['wh_number']), formats['number_sd'])
                col += 1
                sheet.write(row, col, d['get_wh_vat'], formats['number'])

                row += 1
                contador_datos_compras += 1
            row_suma_fin = row
            # imprimir totales y resumen
            row += 1
            col = 11
            row_totales = row + 1
            sheet.write(row, col, 'TOTALES', formats['title'])
            col = 12
            sheet.write(row, col, '=SUM(M%s:M%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 13
            sheet.write(row, col, '=SUM(N%s:N%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 14
            sheet.write(row, col, '=SUM(O%s:O%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 15
            sheet.write(row, col, '', formats['title_number'])
            col = 16
            sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 17
            sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 18
            sheet.write(row, col, '', formats['title_number'])
            col = 19
            sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 20
            sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 21
            sheet.write(row, col, '', formats['title_number'])
            col = 22
            sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 23
            sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 24
            sheet.write(row, col, '', formats['title_number'])
            col = 25
            sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 26
            sheet.write(row, col, '', formats['title_number'])
            col = 27
            sheet.write(row, col, '', formats['title_number'])
            col = 28
            sheet.write(row, col, '', formats['title_number'])
            col = 29
            sheet.write(row, col, '=SUM(AD%s:AD%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])

            # resumen
            row += 4
            sheet.set_row(row - 1, 25)
            sheet.merge_range('L%s:T%s' % (row, row), 'Resumen de Libro de Compras', formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), 'Base Imponible', formats['title'])
            sheet.merge_range('Z%s:AC%s' % (row, row), 'Crédito Fiscal', formats['title'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row), 'Compras Internas no Gravadas y/o Sin Derecho a Crédito Fiscal')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row), 'Compras Internas gravadas por Alicuota General ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=O%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Q%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Compras Internas gravadas por Alicuota General mas Alicuota Adicional ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=U%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=W%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Compras Internas gravadas por Alicuota Reducida')
            sheet.merge_range('U%s:Y%s' % (row, row), '=R%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=T%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas Alícuota General ')
            sheet.merge_range('U%s:Y%s' % (row, row), '=X%s' % row_totales, formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Z%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas por Alícuota General mas Adicional ')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Importaciones gravadas por Alicuota Reducida')
            sheet.merge_range('U%s:Y%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Total Compras y Créditos Fiscales ',
                              formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), '=O%s' % row_totales, formats['title_number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=Q%s' % row_totales, formats['title_number'])
            row += 1
            sheet.merge_range('L%s:T%s' % (row, row),
                              'Total IVA Retenido',
                              formats['title'])
            sheet.merge_range('U%s:Y%s' % (row, row), '', formats['title_number'])
            sheet.merge_range('Z%s:AC%s' % (row, row), '=AD%s' % row_totales, formats['title_number'])

            row += 3
            col = 1
            sheet.merge_range('B%s:G%s' % (row, row), 'AJUSTE A CREDITOS FISCALES PERIODOS ANTERIORES')
            row += 1
            if datos_compras_ajustes:
                for title in titles:
                    sheet.write(row, col, title[1], formats['title'])
                    col += 1
                row += 1
                col = 1

                contador_datos_compras_ajustes = 1
                row_suma_ini_ajustes = row
                for d in datos_compras_ajustes:
                    col = 1
                    sheet.write(row, col, contador_datos_compras_ajustes)
                    col += 1
                    sheet.write(row, col, d['emission_date'])
                    col += 1
                    sheet.write(row, col, d['partner_vat'])
                    col += 1
                    sheet.write(row, col, d['partner_name'])
                    col += 1
                    sheet.write(row, col, d['people_type'])
                    col += 1
                    sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['ctrl_number'], formats['string'])
                    col += 1
                    sheet.write(row, col, d['credit_affected'] if d['doc_type'] == 'N/CR' else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['debit_affected'] if d['debit_affected'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['type'])
                    col += 1
                    sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '', formats['string'])
                    col += 1
                    sheet.write(row, col, d['total_with_iva'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_exempt'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax_importaciones'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['nro_planilla'], formats['string'])
                    col += 1
                    sheet.write(row, col, d['nro_expediente'], formats['string'])
                    col += 1
                    sheet.write(row, col, str(d['wh_number']), formats['number_sd'])
                    col += 1
                    sheet.write(row, col, d['get_wh_vat'], formats['number'])

                    row += 1
                    contador_datos_compras_ajustes += 1
                row_suma_fin_ajustes = row
                # imprimir totales y resumen en ajustes
                row += 1
                col = 11
                sheet.write(row, col, 'TOTALES', formats['title'])
                col = 12
                sheet.write(row, col, '=SUM(M%s:M%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 13
                sheet.write(row, col, '=SUM(N%s:N%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 14
                sheet.write(row, col, '=SUM(O%s:O%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 15
                sheet.write(row, col, '', formats['title_number'])
                col = 16
                sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 17
                sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 18
                sheet.write(row, col, '', formats['title_number'])
                col = 19
                sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 20
                sheet.write(row, col, '=SUM(U%s:U%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 21
                sheet.write(row, col, '', formats['title_number'])
                col = 22
                sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 23
                sheet.write(row, col, '=SUM(X%s:X%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 24
                sheet.write(row, col, '', formats['title_number'])
                col = 25
                sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])
                col = 26
                sheet.write(row, col, '', formats['title_number'])
                col = 27
                sheet.write(row, col, '', formats['title_number'])
                col = 28
                sheet.write(row, col, '', formats['title_number'])
                col = 29
                sheet.write(row, col, '=SUM(AD%s:AD%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes),
                            formats['title_number'])

            sheet.set_column('AC:AC', 15)

            workbook.close()
            # with open(file_name, "rb") as file:
            #     file_base64 = base64.b64encode(file.read())
            file_base64 = base64.b64encode(output.getvalue())

            file_name = 'Libro de Compra'
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas': file_base64
            })
            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
                'target': 'current',
            }
            return action
        else:
            ##excel de ventas
            file_name = 'Libro_Venta.xlsx'
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'strings_to_numbers': True})
            sheet = workbook.add_worksheet('Libro de Venta')
            formats = self.set_formats(workbook)
            datos_ventas, datos_ventas_ajustes = self.get_datas_ventas()
            print('datos_ventas', datos_ventas)
            print('datos_ventas_ajustes', datos_ventas_ajustes)
            if not datos_ventas and not datos_ventas_ajustes:
                raise UserError('No hay datos disponibles')
            sheet.merge_range('B3:G3', datos_ventas[0]['company_name'] if datos_ventas else datos_ventas_ajustes[0]['company_name'], formats['string_titulo'])
            sheet.merge_range('M3:T3', 'Libro de Venta', formats['string_titulo'])
            sheet.merge_range('B4:G4', datos_ventas[0]['company_rif'] if datos_ventas else datos_ventas_ajustes[0]['company_rif'], formats['string'])
            format_new = "%d/%m/%Y"
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT).date()
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT).date()

            sheet.merge_range('M4:N4', 'Desde', formats['string'])
            sheet.merge_range('O4:P4', '%s' % date_start.strftime(format_new), formats['date'])
            sheet.merge_range('Q4:R4', 'Hasta', formats['string'])
            sheet.merge_range('S4:T4', '%s' % date_end.strftime(format_new), formats['date'])

            sheet.merge_range('Q6:Y6', 'Ventas Internas ó Exportación Gravadas', formats['title'])

            row = 6
            col = 1
            titles = [(1, 'Nro. Op'),
                      (2, 'Nro. Reporte Z'),
                      #(3, 'Nro. Impresora'),
                      (4, 'Fecha Documento'),
                      (5, 'RIF'),
                      (6, 'Nombre ó Razón Social'),
                      (7, 'Tipo Prov.'),
                      (8, 'Nro. Planilla de Exportación'),
                      (9, 'Factura Desde'),
                      (10, 'Factura Hasta'),
                      (11, 'Nro. De Control'),
                      (12, 'Nro. Ultima Factura'),
                      (13, 'Nro. Factura Afectada'),
                      (14, 'Nro. Nota de Débito'),
                      (15, 'Nro. Nota de Crédito'),
                      (16, 'Tipo de Trans.'),
                      (17, 'Ventas Incluyendo IVA'),
                      (18, 'Ventas Internas ó Exportaciones No Gravadas'),
                      (19, 'Ventas Internas ó Exportaciones Exoneradas'),
                      (20, 'Base Imponible Alicuota General'),
                      (21, '% Alícuota General'),
                      (22, 'Impuesto IVA Alicuota General'),
                      (23, 'Base Imponible Alicuota Reducida'),
                      (24, '% Alícuota Reducida'),
                      (25, 'Impuesto IVA Alicuota Reducida'),
                      (26, 'Base Imponible Alicuota Adicional'),
                      (27, '% Alícuota Adicional'),
                      (28, 'Impuesto IVA Alicuota Adicional'),
                      (29, 'IVA Retenido (Comprador)'),
                      (30, 'Nro. De Comprobante'),
                      (31, 'Fecha Comp.')]

            # sheet.set_row(6, cell_format=formats['title'])
            for title in titles:
                sheet.write(row, col, title[1], formats['title'])
                col += 1
            row += 1
            col = 1
            contador_datos_ventas = 1
            row_suma_ini = row
            for d in datos_ventas:
                col = 1
                sheet.write(row, col, contador_datos_ventas)
                col += 1
                sheet.write(row, col, d['report_z'] if d['report_z'] else '')
                col += 1
                # sheet.write(row, col, d['report_z'] if d['report_z'] else '')
                # col += 1
                sheet.write(row, col, d['emission_date'])
                col += 1
                sheet.write(row, col, d['partner_vat'])
                col += 1
                sheet.write(row, col, d['partner_name'])
                col += 1
                sheet.write(row, col, d['people_type'])
                col += 1
                sheet.write(row, col, d['export_form'])
                col += 1
                sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else (d['fac_desde'] if d['fac_desde'] else ''))
                col += 1
                sheet.write(row, col, d['fac_hasta'] if d['fac_hasta'] else '')
                col += 1
                sheet.write(row, col, d['ctrl_number'] if d['ctrl_number'] else '')
                col += 1
                sheet.write(row, col, d['n_ultima_factZ'] if d['n_ultima_factZ'] else '')
                col += 1
                sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '')
                col += 1
                sheet.write(row, col, d['debit_note'] if d['debit_note'] else '')
                col += 1
                sheet.write(row, col, d['credit_note'] if d['credit_note'] else '')
                col += 1
                sheet.write(row, col, d['type'])
                col += 1
                sheet.write(row, col, d['total_w_iva'], formats['number'])
                col += 1
                sheet.write(row, col, d['no_taxe_sale'], formats['number'])
                col += 1
                sheet.write(row, col, d['export_sale'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_general_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_base'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                col += 1
                sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                col += 1
                sheet.write(row, col, d['get_wh_vat'], formats['number'])
                col += 1
                sheet.write(row, col, d['wh_number'] if d['wh_number'] else '')
                col += 1
                sheet.write(row, col, d['date_wh_number'] if d['date_wh_number'] else '')

                row += 1
                contador_datos_ventas += 1

            row_suma_fin = row
            # imprimir totales y resumen
            row += 1
            col = 15
            row_totales = row + 1
            sheet.write(row, col, 'TOTALES', formats['title'])
            col = 16
            sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 17
            sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 18
            sheet.write(row, col, '=SUM(S%s:S%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 19
            sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 20
            sheet.write(row, col, '', formats['title_number'])
            col = 21
            sheet.write(row, col, '=SUM(V%s:V%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 22
            sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 23
            sheet.write(row, col, '', formats['title_number'])
            col = 24
            sheet.write(row, col, '=SUM(Y%s:Y%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 25
            sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 26
            sheet.write(row, col, '', formats['title_number'])
            col = 27
            sheet.write(row, col, '=SUM(AB%s:AB%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 28
            sheet.write(row, col, '=SUM(AC%s:AC%s)' % (row_suma_ini, row_suma_fin), formats['title_number'])
            col = 29
            sheet.write(row, col, '', formats['title_number'])
            col = 30
            sheet.write(row, col, '', formats['title_number'])

            # resumen
            row += 4

            sheet.merge_range('L%s:R%s' % (row, row), 'Resumen de Libro de Ventas', formats['title'])
            sheet.merge_range('S%s:U%s' % (row, row), 'Base Imponible', formats['title'])
            sheet.merge_range('V%s:X%s' % (row, row), 'Débito Fiscal', formats['title'])
            sheet.merge_range('Y%s:AA%s' % (row, row), 'IVA Retenido por el Comprador', formats['title'])
            row += 1
            row_resumen = row
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas Exoneradas')
            sheet.merge_range('S%s:U%s' % (row, row), '=R%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas de Exportación')
            sheet.merge_range('S%s:U%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '0.0', formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas gravadas por Alicuota General')
            sheet.merge_range('S%s:U%s' % (row, row), '=T%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=V%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '=AC%s' % row_totales, formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row),
                              'Ventas Internas gravadas por Alicuota General mas Alicuota Adicional ')
            sheet.merge_range('S%s:U%s' % (row, row), '=X%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=AB%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Ventas Internas gravadas por Alicuota Reducida')
            sheet.merge_range('S%s:U%s' % (row, row), '=W%s' % row_totales, formats['number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=Y%s' % row_totales, formats['number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '0.0', formats['number'])
            row += 1
            sheet.merge_range('L%s:R%s' % (row, row), 'Total Ventas y Debitos Fiscales', formats['title'])
            sheet.merge_range('S%s:U%s' % (row, row), '=SUMA(S%s:U%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            sheet.merge_range('V%s:X%s' % (row, row), '=SUMA(V%s:X%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            sheet.merge_range('Y%s:AA%s' % (row, row), '=SUMA(Y%s:AA%s)' % (row_resumen, row - 1),
                              formats['title_number'])
            row += 1
            if datos_ventas_ajustes:
                row += 3
                col = 1
                sheet.merge_range('B%s:G%s' % (row, row), 'RETENCIONES DE PERIODOS ANTERIORES')
                row += 1
                for title in titles:
                    sheet.write(row, col, title[1], formats['title'])
                    col += 1
                row += 1
                col = 1
                contador_datos_ventas_ajustes = 1
                row_suma_ini_ajustes = row
                for d in datos_ventas_ajustes:
                    col = 1
                    sheet.write(row, col, contador_datos_ventas_ajustes)
                    col += 1
                    sheet.write(row, col, d['report_z'] if d['report_z'] else '')
                    col += 1
                    sheet.write(row, col, d['emission_date'])
                    col += 1
                    sheet.write(row, col, d['partner_vat'])
                    col += 1
                    sheet.write(row, col, d['partner_name'])
                    col += 1
                    sheet.write(row, col, d['people_type'])
                    col += 1
                    sheet.write(row, col, d['export_form'])
                    col += 1
                    sheet.write(row, col, d['invoice_number'] if d['invoice_number'] else (
                        d['fac_desde'] if d['fac_desde'] else ''))
                    col += 1
                    sheet.write(row, col, d['fac_hasta'] if d['fac_hasta'] else '')
                    col += 1
                    sheet.write(row, col, d['ctrl_number'] if d['ctrl_number'] else '')
                    col += 1
                    sheet.write(row, col, d['n_ultima_factZ'] if d['n_ultima_factZ'] else '')
                    col += 1
                    sheet.write(row, col, d['affected_invoice'] if d['affected_invoice'] else '')
                    col += 1
                    sheet.write(row, col, d['debit_note'] if d['debit_note'] else '')
                    col += 1
                    sheet.write(row, col, d['credit_note'] if d['credit_note'] else '')
                    col += 1
                    sheet.write(row, col, d['type'])
                    col += 1
                    sheet.write(row, col, d['total_w_iva'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['no_taxe_sale'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['export_sale'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_general_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_reduced_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_base'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_rate'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['vat_additional_tax'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['get_wh_vat'], formats['number'])
                    col += 1
                    sheet.write(row, col, d['wh_number'] if d['wh_number'] else '')
                    col += 1
                    sheet.write(row, col, d['date_wh_number'] if d['date_wh_number'] else '')

                    row += 1
                    contador_datos_ventas_ajustes += 1

                row_suma_fin_ajustes = row
                # imprimir totales y resumen
                row += 1
                col = 15
                row_totales = row + 1
                sheet.write(row, col, 'TOTALES', formats['title'])
                col = 16
                sheet.write(row, col, '=SUM(Q%s:Q%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 17
                sheet.write(row, col, '=SUM(R%s:R%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 18
                sheet.write(row, col, '=SUM(S%s:S%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 19
                sheet.write(row, col, '=SUM(T%s:T%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 20
                sheet.write(row, col, '', formats['title_number'])
                col = 21
                sheet.write(row, col, '=SUM(V%s:V%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 22
                sheet.write(row, col, '=SUM(W%s:W%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 23
                sheet.write(row, col, '', formats['title_number'])
                col = 24
                sheet.write(row, col, '=SUM(Y%s:Y%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 25
                sheet.write(row, col, '=SUM(Z%s:Z%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 26
                sheet.write(row, col, '', formats['title_number'])
                col = 27
                sheet.write(row, col, '=SUM(AB%s:AB%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 28
                sheet.write(row, col, '=SUM(AC%s:AC%s)' % (row_suma_ini_ajustes, row_suma_fin_ajustes), formats['title_number'])
                col = 29
                sheet.write(row, col, '', formats['title_number'])
                col = 30
                sheet.write(row, col, '', formats['title_number'])


            workbook.close()
            # with open(file_name, "rb") as file:
            #     file_base64 = base64.b64encode(file.read())
            file_base64 = base64.b64encode(output.getvalue())
            file_name = 'Libro de Venta'
            attachment_id = self.env['ir.attachment'].sudo().create({
                'name': file_name,
                'datas': file_base64
            })
            action = {
                'type': 'ir.actions.act_url',
                'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
                'target': 'current',
            }
            return action

    def get_datas_ventas(self):
        datos_ventas = []
        datos_ventas_ajustes = []
        for rec in self:
            format_new = "%d/%m/%Y"

            # date_start =(data['form']['date_from'])
            # date_end =(data['form']['date_to'])

            fb_id = self.env.context['active_id']
            busq = self.env['account.fiscal.book'].search([('id', '=', fb_id)])
            date_start = datetime.strptime(str(self.date_start), DATE_FORMAT)
            date_end = datetime.strptime(str(self.date_end), DATE_FORMAT)
            # date_start = busq.period_start
            # date_end = busq.period_end
            fbl_obj = self.env['account.fiscal.book.line'].search(
                [('fb_id', '=', busq.id)
                 ], order='rank asc')

            suma_total_w_iva = 0
            suma_no_taxe_sale = 0
            suma_vat_general_base = 0
            suma_total_vat_general_base = 0
            suma_total_vat_general_tax = 0
            suma_total_vat_reduced_base = 0
            suma_total_vat_reduced_tax = 0
            suma_total_vat_additional_base = 0
            suma_total_vat_additional_tax = 0
            suma_vat_general_tax = 0
            suma_vat_reduced_base = 0
            suma_vat_reduced_tax = 0
            suma_vat_additional_base = 0
            suma_vat_additional_tax = 0
            suma_get_wh_vat = 0
            suma_ali_gene_addi = 0
            suma_ali_gene_addi_debit = 0
            total_ventas_base_imponible = 0
            total_ventas_debit_fiscal = 0

            suma_amount_tax = 0

            for line in fbl_obj:
                if line.vat_general_base != 0 or line.vat_reduced_base != 0 or line.vat_additional_base != 0 or line.vat_exempt != 0 or (
                        line.void_form == '03-ANU' and line.invoice_number):
                    vat_general_base = 0
                    vat_general_rate = 0
                    vat_general_tax = 0
                    vat_reduced_base = 0
                    vat_additional_base = 0
                    vat_additional_rate = 0
                    vat_additional_tax = 0
                    vat_reduced_rate = 0
                    vat_reduced_tax = 0

                    if line.type == 'ntp':
                        no_taxe_sale = line.vat_general_base
                    else:
                        no_taxe_sale = 0.0

                    if line.vat_reduced_base and line.vat_reduced_base != 0:
                        vat_reduced_base = line.vat_reduced_base
                        vat_reduced_rate = (
                                line.vat_reduced_base and line.vat_reduced_tax * 100 / line.vat_reduced_base)
                        vat_reduced_rate = int(round(vat_reduced_rate, 0))
                        vat_reduced_tax = line.vat_reduced_tax
                        suma_vat_reduced_base += line.vat_reduced_base
                        suma_vat_reduced_tax += line.vat_reduced_tax

                    if line.vat_additional_base and line.vat_additional_base != 0:
                        vat_additional_base = line.vat_additional_base
                        vat_additional_rate = (
                                line.vat_additional_base and line.vat_additional_tax * 100 / line.vat_additional_base)
                        vat_additional_rate = int(round(vat_additional_rate, 0))
                        vat_additional_tax = line.vat_additional_tax
                        suma_vat_additional_base += line.vat_additional_base
                        suma_vat_additional_tax += line.vat_additional_tax

                    if line.vat_general_base and line.vat_general_base != 0:
                        vat_general_base = line.vat_general_base
                        vat_general_rate = (line.vat_general_tax * 100 / line.vat_general_base)
                        vat_general_rate = int(round(vat_general_rate, 0))
                        vat_general_tax = line.vat_general_tax
                        suma_vat_general_base += line.vat_general_base
                        suma_vat_general_tax += line.vat_general_tax

                    if line.get_wh_vat:
                        suma_get_wh_vat += line.get_wh_vat
                    if vat_reduced_rate == 0:
                        vat_reduced_rate = ''
                    else:
                        vat_reduced_rate = str(vat_reduced_rate)
                    if vat_additional_rate == 0:
                        vat_additional_rate = ''
                    else:
                        vat_additional_rate = str(vat_additional_rate)
                    if vat_general_rate == 0:
                        vat_general_rate = ''

                    if vat_general_rate == '' and vat_reduced_rate == '' and vat_additional_rate == '':
                        vat_general_rate = 0

                    # if  line.void_form == '03-ANU' and line.invoice_number:
                    #     vat_general_base = 0
                    #     vat_general_rate = 0
                    #     vat_general_tax = 0
                    #     vat_reduced_base = 0
                    #     vat_additional_base = 0
                    #     vat_additional_rate = 0
                    #     vat_additional_tax = 0
                    #     vat_reduced_rate = 0
                    #     vat_reduced_tax = 0
                    if line.emission_date >= date_start.date():
                        datos_ventas.append({
                            'rannk': line.rank,
                            'emission_date': datetime.strftime(
                                datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                            'partner_vat': line.partner_vat if line.partner_vat else ' ',
                            'partner_name': line.partner_name,
                            'people_type': line.people_type if line.people_type else ' ',
                            'report_z': line.z_report,
                            'fac_desde': line.fac_desde,
                            'fac_hasta': line.fac_hasta,
                            'export_form': '',
                            'wh_number': line.wh_number,
                            'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                            'invoice_number': line.invoice_number,
                            'n_ultima_factZ': line.n_ultima_factZ,
                            'ctrl_number': line.ctrl_number,
                            'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                            'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                            'type': line.void_form,
                            'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                            'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                            'no_taxe_sale': line.vat_exempt,
                            'export_sale': '',
                            'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                            'vat_general_rate': str(vat_general_rate),
                            # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                            'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                            'vat_reduced_base': line.vat_reduced_base,
                            'vat_reduced_rate': str(vat_reduced_rate),
                            'vat_reduced_tax': vat_reduced_tax,
                            'vat_additional_base': vat_additional_base,
                            'vat_additional_rate': str(vat_additional_rate),
                            'vat_additional_tax': vat_additional_tax,
                            'get_wh_vat': line.get_wh_vat,
                            'company_name': line.fb_id.company_id.name,
                            'company_rif': line.fb_id.company_id.rif
                        })
                    else:
                        datos_ventas_ajustes.append({
                            'rannk': line.rank,
                            'emission_date': datetime.strftime(
                                datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                            'partner_vat': line.partner_vat if line.partner_vat else ' ',
                            'partner_name': line.partner_name,
                            'people_type': line.people_type if line.people_type else ' ',
                            'report_z': line.z_report,
                            'fac_desde': line.fac_desde,
                            'fac_hasta': line.fac_hasta,
                            'export_form': '',
                            'wh_number': line.wh_number,
                            'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                            'invoice_number': line.invoice_number,
                            'n_ultima_factZ': line.n_ultima_factZ,
                            'ctrl_number': line.ctrl_number,
                            'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                            'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                            'type': line.void_form,
                            'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                            'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                            'no_taxe_sale': line.vat_exempt,
                            'export_sale': '',
                            'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                            'vat_general_rate': str(vat_general_rate),
                            # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                            'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                            'vat_reduced_base': line.vat_reduced_base,
                            'vat_reduced_rate': str(vat_reduced_rate),
                            'vat_reduced_tax': vat_reduced_tax,
                            'vat_additional_base': vat_additional_base,
                            'vat_additional_rate': str(vat_additional_rate),
                            'vat_additional_tax': vat_additional_tax,
                            'get_wh_vat': line.get_wh_vat,
                            'company_name': line.fb_id.company_id.name,
                            'company_rif': line.fb_id.company_id.rif
                        })
                    suma_total_w_iva += line.total_with_iva
                    suma_no_taxe_sale += line.vat_exempt
                    suma_total_vat_general_base += line.vat_general_base
                    suma_total_vat_general_tax += line.vat_general_tax
                    suma_total_vat_reduced_base += line.vat_reduced_base
                    suma_total_vat_reduced_tax += line.vat_reduced_tax
                    suma_total_vat_additional_base += line.vat_additional_base
                    suma_total_vat_additional_tax += line.vat_additional_tax

                    # RESUMEN LIBRO DE VENTAS

                    # suma_ali_gene_addi =  suma_vat_additional_base if line.vat_additional_base else 0.0
                    # suma_ali_gene_addi_debit = suma_vat_additional_tax if line.vat_additional_tax else 0.0
                    total_ventas_base_imponible = suma_vat_general_base + suma_vat_additional_base + suma_vat_reduced_base + suma_no_taxe_sale
                    total_ventas_debit_fiscal = suma_vat_general_tax + suma_vat_additional_tax + suma_vat_reduced_tax

            if fbl_obj.env.company and fbl_obj.env.company.street:
                street = str(fbl_obj.env.company.street) + ','
            else:
                street = ' '

        return datos_ventas, datos_ventas_ajustes

class FiscalBookSaleReport(models.AbstractModel):
    _name = 'report.l10n_ve_full.report_fiscal_sale_book'

    @api.model
    def _get_report_values(self, docids, data=None):
        format_new = "%d/%m/%Y"

        # date_start =(data['form']['date_from'])
        # date_end =(data['form']['date_to'])

        fb_id = data['form']['book_id']
        busq = self.env['account.fiscal.book'].search([('id', '=', fb_id)])
        date_start = datetime.strptime(data['form']['date_from'], DATE_FORMAT).date()
        date_end = datetime.strptime(data['form']['date_to'], DATE_FORMAT).date()
        # date_start = busq.period_start
        # date_end = busq.period_end
        fbl_obj = self.env['account.fiscal.book.line'].search(
            [('fb_id', '=', busq.id)
             ], order='rank asc')

        docs = []
        docs_ajustes = []
        suma_total_w_iva = 0
        suma_no_taxe_sale = 0
        suma_vat_general_base = 0
        suma_total_vat_general_base = 0
        suma_total_vat_general_tax = 0
        suma_total_vat_reduced_base = 0
        suma_total_vat_reduced_tax = 0
        suma_total_vat_additional_base = 0
        suma_total_vat_additional_tax = 0
        suma_vat_general_tax = 0
        suma_vat_reduced_base = 0
        suma_vat_reduced_tax = 0
        suma_vat_additional_base = 0
        suma_vat_additional_tax = 0
        suma_get_wh_vat = 0
        suma_ali_gene_addi = 0
        suma_ali_gene_addi_debit = 0
        total_ventas_base_imponible = 0
        total_ventas_debit_fiscal = 0

        suma_amount_tax = 0

        for line in fbl_obj:
            if line.vat_general_base != 0 or line.vat_reduced_base != 0 or line.vat_additional_base != 0 or line.vat_exempt != 0 or (
                    line.void_form == '03-ANU' and line.invoice_number):
                vat_general_base = 0
                vat_general_rate = 0
                vat_general_tax = 0
                vat_reduced_base = 0
                vat_additional_base = 0
                vat_additional_rate = 0
                vat_additional_tax = 0
                vat_reduced_rate = 0
                vat_reduced_tax = 0

                if line.type == 'ntp':
                    no_taxe_sale = line.vat_general_base
                else:
                    no_taxe_sale = 0.0

                if line.vat_reduced_base and line.vat_reduced_base != 0:
                    vat_reduced_base = line.vat_reduced_base
                    vat_reduced_rate = (line.vat_reduced_base and line.vat_reduced_tax * 100 / line.vat_reduced_base)
                    vat_reduced_rate = int(round(vat_reduced_rate, 0))
                    vat_reduced_tax = line.vat_reduced_tax
                    if line.emission_date >= date_start:
                        suma_vat_reduced_base += line.vat_reduced_base
                        suma_vat_reduced_tax += line.vat_reduced_tax

                if line.vat_additional_base and line.vat_additional_base != 0:
                    vat_additional_base = line.vat_additional_base
                    vat_additional_rate = (
                                line.vat_additional_base and line.vat_additional_tax * 100 / line.vat_additional_base)
                    vat_additional_rate = int(round(vat_additional_rate, 0))
                    vat_additional_tax = line.vat_additional_tax
                    if line.emission_date >= date_start:
                        suma_vat_additional_base += line.vat_additional_base
                        suma_vat_additional_tax += line.vat_additional_tax

                if line.vat_general_base and line.vat_general_base != 0:
                    vat_general_base = line.vat_general_base
                    vat_general_rate = (line.vat_general_tax * 100 / line.vat_general_base)
                    vat_general_rate = int(round(vat_general_rate, 0))
                    vat_general_tax = line.vat_general_tax
                    if line.emission_date >= date_start:
                        suma_vat_general_base += line.vat_general_base
                        suma_vat_general_tax += line.vat_general_tax

                if line.get_wh_vat and line.emission_date >= date_start:
                    suma_get_wh_vat += line.get_wh_vat
                if vat_reduced_rate == 0:
                    vat_reduced_rate = ''
                else:
                    vat_reduced_rate = str(vat_reduced_rate)
                if vat_additional_rate == 0:
                    vat_additional_rate = ''
                else:
                    vat_additional_rate = str(vat_additional_rate)
                if vat_general_rate == 0:
                    vat_general_rate = ''

                if vat_general_rate == '' and vat_reduced_rate == '' and vat_additional_rate == '':
                    vat_general_rate = 0

                # if  line.void_form == '03-ANU' and line.invoice_number:
                #     vat_general_base = 0
                #     vat_general_rate = 0
                #     vat_general_tax = 0
                #     vat_reduced_base = 0
                #     vat_additional_base = 0
                #     vat_additional_rate = 0
                #     vat_additional_tax = 0
                #     vat_reduced_rate = 0
                #     vat_reduced_tax = 0
                if line.emission_date >= date_start:
                    docs.append({
                        'rannk': line.rank,
                        'emission_date': datetime.strftime(
                            datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                        'partner_vat': line.partner_vat if line.partner_vat else ' ',
                        'partner_name': line.partner_name,
                        'people_type': line.people_type if line.people_type else ' ',
                        'report_z': line.z_report if line.z_report else False,
                        'fiscal_printer': line.fiscal_printer if line.fiscal_printer else False,
                        'fac_desde': line.fac_desde,
                        'fac_hasta': line.fac_hasta,
                        'export_form': '',
                        'wh_number': line.wh_number,
                        'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                        'invoice_number': line.invoice_number,
                        'n_ultima_factZ': line.n_ultima_factZ,
                        'ctrl_number': line.ctrl_number,
                        'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                        'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                        'type': line.void_form,
                        'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                        'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                        'no_taxe_sale': line.vat_exempt,
                        'export_sale': '',
                        'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                        'vat_general_rate': str(vat_general_rate),
                        # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                        'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                        'vat_reduced_base': line.vat_reduced_base,
                        'vat_reduced_rate': str(vat_reduced_rate),
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': str(vat_additional_rate),
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': line.get_wh_vat,
                    })

                    suma_total_w_iva += line.total_with_iva
                    suma_no_taxe_sale += line.vat_exempt
                    suma_total_vat_general_base += line.vat_general_base
                    suma_total_vat_general_tax += line.vat_general_tax
                    suma_total_vat_reduced_base += line.vat_reduced_base
                    suma_total_vat_reduced_tax += line.vat_reduced_tax
                    suma_total_vat_additional_base += line.vat_additional_base
                    suma_total_vat_additional_tax += line.vat_additional_tax

                    # RESUMEN LIBRO DE VENTAS

                    # suma_ali_gene_addi =  suma_vat_additional_base if line.vat_additional_base else 0.0
                    # suma_ali_gene_addi_debit = suma_vat_additional_tax if line.vat_additional_tax else 0.0
                    total_ventas_base_imponible = suma_vat_general_base + suma_vat_additional_base + suma_vat_reduced_base + suma_no_taxe_sale
                    total_ventas_debit_fiscal = suma_vat_general_tax + suma_vat_additional_tax + suma_vat_reduced_tax
                else:
                    docs_ajustes.append({
                        'rannk': line.rank,
                        'emission_date': datetime.strftime(
                            datetime.strptime(str(line.emission_date), DEFAULT_SERVER_DATE_FORMAT), format_new),
                        'partner_vat': line.partner_vat if line.partner_vat else ' ',
                        'partner_name': line.partner_name,
                        'people_type': line.people_type if line.people_type else ' ',
                        'report_z': line.z_report if line.z_report else False,
                        'fiscal_printer': line.fiscal_printer if line.fiscal_printer else False,
                        'fac_desde': line.fac_desde,
                        'fac_hasta': line.fac_hasta,
                        'export_form': '',
                        'wh_number': line.wh_number,
                        'date_wh_number': line.iwdl_id.retention_id.date_ret if line.wh_number != '' else '',
                        'invoice_number': line.invoice_number,
                        'n_ultima_factZ': line.n_ultima_factZ,
                        'ctrl_number': line.ctrl_number,
                        'debit_note': line.numero_debit_credit if line.doc_type == 'N/DB' else False,
                        'credit_note': line.numero_debit_credit if line.doc_type == 'N/CR' else False,
                        'type': line.void_form,
                        'affected_invoice': line.affected_invoice if line.affected_invoice else ' ',
                        'total_w_iva': line.total_with_iva if line.total_with_iva else 0,
                        'no_taxe_sale': line.vat_exempt,
                        'export_sale': '',
                        'vat_general_base': vat_general_base,  # + vat_reduced_base + vat_additional_base,
                        'vat_general_rate': str(vat_general_rate),
                        # + '  ' + str(vat_reduced_rate) + ' ' + str(vat_additional_rate) + '  ',
                        'vat_general_tax': vat_general_tax,  # + vat_reduced_tax + vat_additional_tax,
                        'vat_reduced_base': line.vat_reduced_base,
                        'vat_reduced_rate': str(vat_reduced_rate),
                        'vat_reduced_tax': vat_reduced_tax,
                        'vat_additional_base': vat_additional_base,
                        'vat_additional_rate': str(vat_additional_rate),
                        'vat_additional_tax': vat_additional_tax,
                        'get_wh_vat': line.get_wh_vat,
                    })



        date_start = datetime.strftime(datetime.strptime(data['form']['date_from'], DEFAULT_SERVER_DATE_FORMAT),
                                       format_new)
        date_end = datetime.strftime(datetime.strptime(data['form']['date_to'], DEFAULT_SERVER_DATE_FORMAT), format_new)

        if fbl_obj.fb_id.company_id and fbl_obj.fb_id.company_id.street:
            street = str(fbl_obj.fb_id.company_id.street) + ','
        else:
            street = ' '

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'date_start': date_start,
            'date_end': date_end,
            'docs': docs,
            'docs_ajustes': docs_ajustes,
            'a': 0.00,
            'street': street,
            'company': fbl_obj.fb_id.company_id,
            'suma_total_w_iva': suma_total_w_iva,
            'suma_no_taxe_sale': suma_no_taxe_sale,
            'suma_total_vat_general_base': suma_total_vat_general_base,
            'suma_total_vat_general_tax': suma_total_vat_general_tax,
            'suma_vat_general_base': suma_vat_general_base,
            'suma_vat_general_tax': suma_vat_general_tax,
            'suma_total_vat_reduced_base': suma_total_vat_reduced_base,
            'suma_total_vat_reduced_tax': suma_total_vat_reduced_tax,
            'suma_total_vat_additional_base': suma_total_vat_additional_base,
            'suma_total_vat_additional_tax': suma_total_vat_additional_tax,
            'suma_vat_reduced_base': suma_vat_reduced_base,
            'suma_vat_reduced_tax': suma_vat_reduced_tax,
            'suma_vat_additional_base': suma_vat_additional_base,
            'suma_vat_additional_tax': suma_vat_additional_tax,
            'suma_get_wh_vat': suma_get_wh_vat,
            'suma_ali_gene_addi': suma_vat_additional_base,
            'suma_ali_gene_addi_debit': suma_vat_additional_tax,
            'total_ventas_base_imponible': total_ventas_base_imponible,
            'total_ventas_debit_fiscal': total_ventas_debit_fiscal,
        }
#
#
# FiscalBookWizard()

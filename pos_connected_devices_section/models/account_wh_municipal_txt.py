# coding: utf-8
from odoo import fields, models, api
from odoo.exceptions import UserError
import base64


class AccountWhMunicipalTxt(models.Model):
    _name = 'account.wh.municipal.txt'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'TXT de retención municipal'

    name = fields.Char('NRO.', required=True, copy=False, readonly=True, index=True, default=lambda self: ('New'))

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)
    date_from = fields.Date('Desde', required=True)
    date_to = fields.Date('Hasta', required=True)

    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)

    codigo_asignado = fields.Char('Licencia Municipal', related='company_id.partner_id.codigo_asignado',
                                  readonly=True)

    currency_id = fields.Many2one('res.currency', string='Moneda', required=True,
                                  default=lambda self: self.env.company.currency_id)

    amount_total = fields.Monetary('Total', compute='_compute_amount_total', store=True, currency_field='currency_id')

    txt_filename = fields.Char('Nombre del archivo', size=256, readonly=True)
    txt_file = fields.Binary('Archivo TXT', readonly=True)

    invoice_ids = fields.Many2many('account.move', string='Facturas', required=True,
                                   domain=[('move_type', '=', 'in_invoice'), ('state', 'in', ['posted']),
                                           ('wh_muni_id', '!=', False)])



    @api.depends('invoice_ids')
    def _compute_amount_total(self):
        for txt in self:
            txt.amount_total = sum(invoice.monto_reten_muni for invoice in txt.invoice_ids)

    def generate_txt(self):
        # Reemplazar método para generar el archivo TXT segun la estructura del Municipio

        # verifica si la compañia tiene licencia municipal
        if not self.company_id.partner_id.codigo_asignado:
            raise UserError('La compañía no tiene el código asignado, verifique en la ficha de la compañía, pestaña "Retenciones"')
        # # verifica si hay facturas cuyos proveedores no tienen licencia municipal
        # if self.invoice_ids.filtered(lambda invoice: not invoice.partner_id.licencia_municipal):
        #     raise UserError(
        #         'Uno o más proveedores no tienen licencia municipal, verifique en la ficha del proveedor, pestaña "Retenciones"')

        #obtener el mes del periodo en letras
        mes_periodo = self.date_from.strftime('%B')
        # Se refiere si la Retención a enterar corresponde a la 1ra. o 2da. Quincena del Período en cuestión.
        quincena = '1' if self.date_from.day <= 15 else '2'
        self.txt_filename = 'retencion' + mes_periodo + quincena + '.txt'
        txt_file = ''
        for invoice in self.invoice_ids:
            codigo_asignado = self.company_id.partner_id.codigo_asignado
            # completar con 0 a la izquierda hasta 5 caracteres
            codigo_asignado = codigo_asignado.zfill(5)
            txt_file += '%s' % codigo_asignado
            # agregar tabulador
            txt_file += '\t'
            # agregar rif
            txt_file += self.company_id.partner_id.rif
            # agregar tabulador
            txt_file += '\t'
            # agregar Tipo de Contribuyente
            txt_file += invoice.partner_id.tipo_contribuyente_mun if invoice.partner_id.codigo_asignado else 'T'
            # agregar tabulador
            txt_file += '\t'
            # agregar año del periodo
            txt_file += self.date_from.strftime('%Y')
            # agregar tabulador
            txt_file += '\t'
            # agregar mes del periodo
            txt_file += self.date_from.strftime('%m')
            # agregar tabulador
            txt_file += '\t'
            # Código que Corresponde al Contribuyente Domiciliado en el Municipio Páez Numérico 5 Caracteres, completar con ceros a la izquierda (“Colocar 00000 si no lo posee o es Transeúnte”)
            txt_file += invoice.partner_id.codigo_asignado.zfill(5) if invoice.partner_id.codigo_asignado else '00000'
            # agregar tabulador
            txt_file += '\t'
            # Corresponde al R.I.F. del Contribuyente o Agente Retenido.
            txt_file += invoice.partner_id.rif
            # agregar tabulador
            txt_file += '\t'
            # Corresponde al Nombre o Denominación Comercial del Contribuyente o Agente Retenido.
            txt_file += invoice.partner_id.name.strip()
            # agregar tabulador
            txt_file += '\t'
            # Corresponde a la Fecha del Documento de Cobranza o Factura. DD/MM/AAAA
            txt_file += invoice.invoice_date.strftime('%d/%m/%Y')
            # agregar tabulador
            txt_file += '\t'
            # Corresponde al Número del Documento de Cobranza o Factura.
            txt_file += invoice.supplier_invoice_number
            # agregar tabulador
            txt_file += '\t'
            # Número de Control del Documento de Cobranza o Factura.
            txt_file += invoice.nro_ctrl
            # agregar tabulador
            txt_file += '\t'
            # NUMERO DE COMPROBANTE DE RETENCIÓN:
            txt_file += invoice.wh_muni_id.name
            # agregar tabulador
            txt_file += '\t'
            # agregar la fecha de la retención
            txt_file += invoice.wh_muni_id.date.strftime('%d/%m/%Y')
            # agregar tabulador
            txt_file += '\t'
            # se refiere al Monto Bruto del Documento de Cobranza o Factura.
            txt_file += '%s' % ("{:.2f}".format(invoice.amount_total)).replace('.', ',')
            # agregar tabulador
            txt_file += '\t'
            # agregar porcentaje de retencion
            txt_file += '%s' % ("{:.2f}".format(invoice.rate_value)).replace('.', ',') + '%'
            # agregar tabulador
            txt_file += '\t'
            # Se refiere al Monto resultante del % que se Aplicó al Monto Bruto del Documento de Cobranza o Factura.
            txt_file += '%s' % ("{:.2f}".format(invoice.monto_reten_muni)).replace('.', ',')
            # agregar tabulador
            txt_file += '\t'
            # Se refiere si la Retención a enterar corresponde a la 1ra. o 2da. Quincena del Período en cuestión.
            txt_file += '1' if self.date_from.day <= 15 else '2'
            # agregar salto de linea
            txt_file += '\n'

        self.txt_file = base64.encodebytes(txt_file.encode('utf-8'))


    def create(self, vals):
        if vals.get('name', ('New')) == ('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('account.wh.municipal.txt') or ('New')
        return super(AccountWhMunicipalTxt, self).create(vals)


    def load_invoice(self):
        self.ensure_one()
        if not self.date_from or not self.date_to:
            raise UserError('Debe ingresar las fechas')
        invoices = self.env['account.move'].search(
            [('move_type', '=', 'in_invoice'), ('state', 'in', ['posted']), ('wh_muni_id', '!=', False),
             ('wh_muni_id.date', '>=', self.date_from), ('wh_muni_id.date', '<=', self.date_to),
             ('wh_muni_id.incluida_txt', '=', False)])
        self.invoice_ids = invoices
        self.txt_filename = False
        self.txt_file = False
        return True


    def action_done(self):
        # verifica que tenga el txt generado
        if not self.txt_file:
            raise UserError('Debe generar el archivo TXT antes de marcarlo como Realizado')
        # marcar todas las retenciones de las invoices como declarada en txt
        self.invoice_ids.mapped('wh_muni_id').write({'incluida_txt': True})
        self.write({'state': 'done'})


    def action_cancel(self):
        # marcar todas las retenciones de las invoices como not declarada en txt
        self.invoice_ids.mapped('wh_muni_id').write({'incluida_txt': False})
        self.write({'state': 'cancel'})


    def action_draft(self):
        self.write({'state': 'draft'})
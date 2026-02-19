# coding: utf-8
from odoo import fields, models, api
from odoo.exceptions import UserError


class AccountWhMunicipalDocs(models.Model):
    _name = 'account.wh.municipal.docs'
    _check_company_auto = True
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Documentos de retención municipal'

    name = fields.Char('NRO. COMPROBANTE', required=True)

    partner_id = fields.Many2one('res.partner', string='Proveedor', required=True)
    date = fields.Date('Fecha', required=True)
    periodo_fiscal = fields.Char('Período Fiscal', compute='_compute_periodo_fiscal', store=True)
    amount_total = fields.Monetary('Total retenido', currency_field='currency_id', compute='_compute_amount_total', store=True)
    currency_id = fields.Many2one('res.currency', string='Moneda', required=True, default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('done', 'Realizado'),
        ('cancel', 'Cancelado'),
    ], string='Estado', default='draft', required=True)

    type = fields.Selection([
        ('in_invoice', 'Facturas de Proveedor'),
        ('out_invoice', 'Facturas de Cliente'),
    ], string='Tipo', required=True)

    company_id = fields.Many2one('res.company', string='Compañía', required=True, default=lambda self: self.env.company)
    journal_id = fields.Many2one('account.journal', string='Diario')
    line_ids = fields.One2many('account.wh.municipal.docs.lines', 'wh_municipal_id', string='Líneas de documentos de retención municipal')

    incluida_txt = fields.Boolean('Incluida en TXT', default=False)

    @api.onchange('date','state')
    def _compute_periodo_fiscal(self):
        for rec in self:
            rec.periodo_fiscal = rec.date.strftime('%m-%Y')

    @api.depends('line_ids')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum(rec.line_ids.mapped('monto_reten_muni'))


    def action_post(self):

        if not self.name or self.name == '':
            raise UserError('Debe ingresar el número de comprobante')

        #verificar si ya se ha realizado la retención a las facturas en la lista
        for line in self.line_ids:
            if line.invoice_id.account_move_ret_muni_id:
                if line.invoice_id.account_move_ret_muni_id.state != 'posted':
                    raise UserError('El asiento de retención %s no ha sido validado' % line.invoice_id.account_move_ret_muni_id.name)
            else:
                raise UserError('La factura %s no ha sido retenida' % line.invoice_id.name)
        self.write({'state': 'done'})


class AccountWhMunicipalDocsLines(models.Model):
    _name = 'account.wh.municipal.docs.lines'
    _check_company_auto = True
    _description = 'Líneas de documentos de retención municipal'

    wh_municipal_id = fields.Many2one('account.wh.municipal.docs', string='Documento de retención', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Moneda', related='wh_municipal_id.currency_id', store=True)
    invoice_id = fields.Many2one('account.move', string='Factura', required=True)
    municipal_rate_id = fields.Many2one('account.wh.municipal.rates', string='Concepto', related='invoice_id.municipal_rate_id', store=True)
    rate_value = fields.Float('Alícuota', related='invoice_id.rate_value', store=True)
    porc_reten_muni = fields.Float('Porcentaje de retención municipal', related='invoice_id.porc_reten_muni', store=True)
    monto_reten_muni = fields.Monetary('Monto', related='invoice_id.monto_reten_muni', store=True, currency_field='currency_id')
    company_id = fields.Many2one('res.company', string='Compañía', related='invoice_id.company_id', store=True)
    name = fields.Char('Número de Retención', related='wh_municipal_id.name', store=True)



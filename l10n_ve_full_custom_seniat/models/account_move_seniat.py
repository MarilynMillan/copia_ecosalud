from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import formatLang
from odoo.tools import float_is_zero
import re

class AccountMoveSeniat(models.Model):
    _inherit = 'account.move'

    _sql_constraints = [
        ('nro_ctrl_uniq', 'unique(nro_ctrl, company_id, move_type, journal_id)', 
         '¡ERROR CRÍTICO! El Número de Control ya existe. No puede haber duplicados (Providencia 0071).')
    ]

    wh_iva_state = fields.Selection([
        ('draft', 'Borrador'), ('confirmed', 'Confirmado'),
        ('done', 'Realizado'), ('cancel', 'Cancelado')
    ], string='Estado Ret. IVA', compute='_compute_wh_states', store=False)
    
    wh_islr_state = fields.Selection([
        ('draft', 'Borrador'), ('confirmed', 'Confirmado'),
        ('done', 'Realizado'), ('cancel', 'Cancelado')
    ], string='Estado Ret. ISLR', compute='_compute_wh_states', store=False)

    igtf_label = fields.Char(compute='_compute_igtf_label')
    total_with_igtf_usd = fields.Monetary(string='Total Ref:', currency_field='currency_id_dif',
        compute='_compute_igtf_values_seniat', store=True)

    def action_post(self):
        for rec in self:
            # Validación 1: No permitir facturar sin número de control para facturas de cliente
            if rec.move_type in ['out_invoice', 'out_refund'] and not rec.nro_ctrl:
                raise UserError(_('¡ERROR FISCAL! No puede publicar una factura de cliente sin Número de Control asignado (Providencia 0071).'))
            
            # Validación 2: No permitir líneas con precio cero (PARA TODOS LOS DOCUMENTOS FISCALES)
            valid_doc_types = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund', 
                             'out_receipt', 'in_receipt', 'out_debit', 'in_debit']
            if rec.move_type in valid_doc_types:
                rec._check_zero_prices() 
                
            # Validación existente de consecutividad (se mantiene solo para facturas de cliente)
            if rec.move_type in ['out_invoice', 'out_refund'] and rec.nro_ctrl:
                rec._check_consecutive_nro_ctrl()
                
        return super(AccountMoveSeniat, self).action_post()
    
    def _check_zero_prices(self):
        precision = self.env['decimal.precision'].precision_get('Product Price')
        lines_with_zero = []
        
        for line in self.invoice_line_ids:
            # VALIDACIÓN COMPLETA - Cubre todos los casos
            # Solo líneas que son realmente productos/servicios facturables
            if (not line.display_type and                    # No es sección/nota
                not line.exclude_from_invoice_tab and        # No está excluida de factura
                line.product_id and                          # Tiene producto asignado
                float_is_zero(line.price_unit, precision_digits=precision)):  # Precio es cero
                
                lines_with_zero.append(f"{line.product_id.name}")
        
        if lines_with_zero:
            # Mensaje estandarizado para todos los documentos
            doc_type_names = {
                'out_invoice': 'Factura de Cliente',
                'in_invoice': 'Factura de Proveedor', 
                'out_refund': 'Nota de Crédito de Cliente',
                'in_refund': 'Nota de Crédito de Proveedor',
                'out_debit': 'Nota de Débito de Cliente',
                'in_debit': 'Nota de Débito de Proveedor',
                'out_receipt': 'Recibo de Cliente',
                'in_receipt': 'Recibo de Proveedor'
            }
            doc_name = doc_type_names.get(self.move_type, 'Documento')
            
            raise UserError(_('¡ERROR FISCAL! No puede publicar %s con productos a precio cero:\n\n• %s\n\nAjuste los precios antes de validar. (Normativa SENIAT - Providencia 0071)') % (doc_name, '\n• '.join(lines_with_zero)))

    def _check_consecutive_nro_ctrl(self):
        self.ensure_one()
        is_repost = self.message_ids.filtered(lambda m: 'Documento restablecido a borrador' in m.body)
        if is_repost: return

        digits = re.findall(r'\d+', self.nro_ctrl)
        if not digits: return 
        
        current_num = int(''.join(digits))
        
        last_invoice = self.search([
            ('move_type', '=', self.move_type),
            ('journal_id', '=', self.journal_id.id),
            ('company_id', '=', self.company_id.id),
            ('state', '=', 'posted'), 
            ('id', '!=', self.id),
            ('nro_ctrl', '!=', False)
        ], order='nro_ctrl desc', limit=1)

        if last_invoice:
            last_digits = re.findall(r'\d+', last_invoice.nro_ctrl)
            if last_digits:
                last_num = int(''.join(last_digits))
                if current_num > (last_num + 1):
                    msg = _('¡ERROR DE CONSECUTIVIDAD! (SENIAT)\n\n'
                            'El Número de Control ingresado es %s.\n'
                            'El último registrado fue %s.\n\n'
                            'Se ha detectado un salto de %s números.\n'
                            'Debe corregir el número de control para mantener la secuencia.') % (
                                self.nro_ctrl, last_invoice.nro_ctrl, (current_num - last_num - 1)
                            )
                    raise ValidationError(msg)

    @api.depends('state')
    def _compute_wh_states(self):
        for rec in self:
            iva_state = False
            if rec.rela_wh_iva:
                iva_state = rec.rela_wh_iva.state
            else:
                wh_iva = self.env['account.wh.iva'].search([
                    ('wh_lines.invoice_id', '=', rec.id), ('state', '!=', 'cancel')
                ], limit=1, order='id desc')
                if wh_iva:
                    iva_state = wh_iva.state
                    if not rec.rela_wh_iva: rec.rela_wh_iva = wh_iva.id
            
            rec.wh_iva_state = iva_state
            if rec.islr_wh_doc_id: rec.wh_islr_state = rec.islr_wh_doc_id.state
            else: rec.wh_islr_state = False

    @api.depends('company_id.igtf_divisa_porcentage')
    def _compute_igtf_label(self):
        for rec in self:
            porc = rec.company_id.igtf_divisa_porcentage
            porc_str = f'{porc:g}'
            rec.igtf_label = f'IGTF {porc_str}%'

    @api.depends('igtf_aplicado', 'amount_total_usd')
    def _compute_igtf_values_seniat(self):
        for rec in self:
            rec.total_with_igtf_usd = (rec.amount_total_usd + rec.igtf_aplicado) if rec.igtf_aplicado else rec.amount_total_usd

    def _compute_tax_totals(self):
        super()._compute_tax_totals()
        for move in self:
            if move.igtf_aplicado > 0 and move.tax_totals:
                totals = dict(move.tax_totals)
                tasa = move.tax_today if move.tax_today else 1.0
                igtf_bs = move.igtf_aplicado * tasa
                
                if 'groups_by_subtotal' in totals and totals['groups_by_subtotal']:
                    subtotal_key = list(totals['groups_by_subtotal'].keys())[0]
                    totals['groups_by_subtotal'][subtotal_key].append({
                        'tax_group_name': move.igtf_label or 'IGTF',
                        'tax_group_amount': igtf_bs,
                        'formatted_tax_group_amount': formatLang(self.env, igtf_bs, currency_obj=move.company_id.currency_id),
                        'tax_group_id': 'igtf_custom_fake_id',
                        'tax_group_base_amount': move.amount_total,
                        'formatted_tax_group_base_amount': formatLang(self.env, move.amount_total, currency_obj=move.company_id.currency_id),
                    })
                    new_total = totals['amount_total'] + igtf_bs
                    totals['amount_total'] = new_total
                    totals['formatted_amount_total'] = formatLang(self.env, new_total, currency_obj=move.company_id.currency_id)
                    move.tax_totals = totals

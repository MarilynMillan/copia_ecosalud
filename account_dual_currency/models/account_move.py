# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from odoo.tools import (
    date_utils,
    email_re,
    email_split,
    float_compare,
    float_is_zero,
    format_amount,
    format_date,
    formatLang,
    frozendict,
    get_lang,
    is_html_empty,
    sql
)
import json

TYPE_REVERSE_MAP = {
    'entry': 'entry',
    'out_invoice': 'out_refund',
    'out_refund': 'entry',
    'in_invoice': 'in_refund',
    'in_refund': 'entry',
    'out_receipt': 'out_refund',
    'in_receipt': 'in_refund',
}

class AccountMove(models.Model):
    _inherit = 'account.move'

    currency_id_dif = fields.Many2one("res.currency",
                                      string="Moneda Dual Ref.",
                                      default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')],
                                                                                           limit=1), )

    acuerdo_moneda = fields.Boolean(string="Acuerdo de Factura Bs.", default=False)

    tax_today = fields.Float(string="Tasa", store=True,
                             default=lambda self: self.env.company.currency_id_dif.inverse_company_rate,
                             tracking=True, digits='Dual_Currency_rate')

    tax_today_edited = fields.Boolean(string="Tasa editada", default=False)

    edit_trm = fields.Boolean(string="Editar tasa", compute='_edit_trm')

    name_rate = fields.Char(store=True, readonly=True, compute='_name_ref')
    amount_untaxed_usd = fields.Monetary(currency_field='currency_id_dif', string="Base imponible Ref.", store=True,
                                         compute="_amount_all_usd", digits='Dual_Currency', copy=False, precompute=True)
    amount_tax_usd = fields.Monetary(currency_field='currency_id_dif', string="Impuestos Ref.", store=True,
                                     readonly=True, digits='Dual_Currency', compute="_amount_all_usd", copy=False)
    amount_total_usd = fields.Monetary(currency_field='currency_id_dif', string='Total Ref.', store=True, readonly=True,
                                       compute='_amount_all_usd',
                                       digits='Dual_Currency', tracking=True)

    amount_residual_usd = fields.Monetary(currency_field='currency_id_dif', compute='_compute_amount', string='Adeudado Ref.',
                                          readonly=True, digits='Dual_Currency', store=True, copy=False)
    invoice_payments_widget_usd = fields.Binary(groups="account.group_account_invoice,account.group_account_readonly",
                                              compute='_compute_payments_widget_reconciled_info_USD')

    amount_untaxed_bs = fields.Monetary(currency_field='company_currency_id', string="Base imponible Bs.", store=True, copy=False,
                                        compute="_amount_all_usd")
    amount_tax_bs = fields.Monetary(currency_field='company_currency_id', string="Impuestos Bs.", store=True, copy=False,
                                    readonly=True, compute="_amount_all_usd")
    amount_total_bs = fields.Monetary(currency_field='company_currency_id', string='Total Bs.', store=True,
                                      readonly=True,
                                      compute='_amount_all_usd', copy=False)

    amount_total_signed_usd = fields.Monetary(
        string='Total Ref.',
        compute='_compute_amount', store=True, readonly=True,
        currency_field='currency_id_dif', copy=False
    )

    invoice_payments_widget_bs = fields.Text(groups="account.group_account_invoice", copy=False)

    same_currency = fields.Boolean(string="Mismo tipo de moneda", compute='_same_currency')

    verificar_pagos = fields.Boolean(string="Verificar pagos", compute='_verificar_pagos')

    asset_remaining_value_ref = fields.Monetary(currency_field='currency_id_dif', string='Valor depreciable Ref.', copy=False, compute='_compute_depreciation_cumulative_value_ref')
    asset_depreciated_value_ref = fields.Monetary(currency_field='currency_id_dif', string='Depreciación Acu. Ref.', copy=False, compute='_compute_depreciation_cumulative_value_ref')

    move_igtf_id = fields.Many2one('account.move', string='Asiento Retención IGTF', copy=False)

    depreciation_value_ref = fields.Monetary(
        string="Depreciation Ref.",
        compute="_compute_depreciation_value_ref", inverse="_inverse_depreciation_value_ref", store=True, copy=False
    )

    igtf_base = fields.Monetary(string="Base IGTF", copy=False, compute='_compute_igtf_aplicado', store=True)

    igtf_aplicado = fields.Monetary(string="IGTF Aplicado", copy=False, compute='_compute_igtf_aplicado', store=True)

    mostrar_igtf_completo = fields.Boolean(string="Mostrar IGTF Completo", default=False)

    crearte_diferencial = fields.Boolean(string="Crear Diferencial", compute='_crearte_diferencial')

    def _crearte_diferencial(self):
        for rec in self:
            crearte_diferencial = False
            if rec.move_type in ('in_invoice', 'in_refund', 'in_receipt', 'out_invoice', 'out_refund', 'out_receipt'):
                payment_term = rec.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                if payment_term:
                    amount = payment_term.debit if payment_term.debit > 0 else payment_term.credit
                    amount_usd = payment_term.debit_usd if payment_term.debit_usd > 0 else payment_term.credit_usd
                    if abs(payment_term.amount_residual_usd) > 0 and abs(payment_term.amount_residual_usd) < amount_usd:
                        crearte_diferencial = True
                    if abs(payment_term.amount_residual) > 0 and abs(payment_term.amount_residual) < amount:
                        crearte_diferencial = True
                if crearte_diferencial:
                    #eliminar de la linea payment_term la conciliacion total
                    if payment_term.full_reconcile_id:
                        payment_term.full_reconcile_id.unlink()
                    payment_term.reconciled = False
                    rec.payment_state = 'partial'
            rec.crearte_diferencial = crearte_diferencial

    def crear_diferencial_cambio(self):
        for rec in self:
            if rec.crearte_diferencial:
                payment_term = rec.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                if payment_term:
                    company_id = rec.company_id if not rec.company_id.parent_id else rec.company_id.parent_id
                    amount_residual = abs(payment_term.amount_residual)
                    amount_residual_usd = abs(payment_term.amount_residual_usd)
                    vals = {
                        'date': rec.date,
                        'journal_id': company_id.currency_exchange_journal_id.id,
                        'currency_id': company_id.currency_id.id,
                        'state': 'draft',
                        'tax_today': 0,
                        'ref': "Diferencial Cambio %s" % rec.name,
                        'move_type': 'entry',
                        'line_ids': [
                            (0, 0, {
                                'account_id': payment_term.account_id.id,
                                'ref': "Diferencial Cambio %s" % rec.name,
                                'partner_id': rec.partner_id.id,
                                'name': "Diferencial Cambio %s" % rec.name,
                                'credit': amount_residual if payment_term.debit > 0 else 0,
                                'credit_usd': amount_residual_usd if payment_term.debit_usd > 0 else 0,
                                'debit': amount_residual if payment_term.credit > 0 else 0,
                                'debit_usd': amount_residual_usd if payment_term.credit_usd > 0 else 0,
                                'no_calcular': True,
                                #'balance_usd': amount_residual_usd if payment_term.debit_usd > 0 else -amount_residual_usd,
                            }),
                            (0, 0, {
                                'account_id': company_id.income_currency_exchange_account_id.id if rec.move_type in ('in_invoice', 'in_refund','in_receipt') else company_id.expense_currency_exchange_account_id.id,
                                'ref': "Diferencial Cambio %s" % rec.name,
                                'name': "Diferencial Cambio %s" % rec.name,
                                'credit': amount_residual if payment_term.credit > 0 else 0,
                                'credit_usd': amount_residual_usd if payment_term.credit_usd > 0 else 0,
                                'debit': amount_residual if payment_term.debit > 0 else 0,
                                'debit_usd': amount_residual_usd if payment_term.debit_usd > 0 else 0,
                                'no_calcular': True,
                                #'balance_usd': amount_residual_usd if payment_term.debit_usd > 0 else -amount_residual_usd,
                            }),
                        ],
                    }

                    ##print('vals', vals)
                    move_id = self.env['account.move'].with_context(check_move_validity=False).create(vals)
                    move_id.action_post()
                    line_to_reconcile = move_id.line_ids.filtered(lambda l: l.account_id == payment_term.account_id)
                    payment_term.reconciled = False
                    (line_to_reconcile + payment_term).reconcile()

    @api.depends('invoice_payments_widget','line_ids.matched_debit_ids', 'line_ids.matched_credit_ids')
    def _compute_igtf_aplicado(self):
        #buscar en todos los pagos aplicados cual tiene igtf
        for rec in self:
            widget = rec.invoice_payments_widget if rec.invoice_payments_widget else {}
            content = widget.get('content', [])
            igtf_base = 0
            igtf_aplicado = 0
            igtf_maximo = (abs(rec.amount_total_usd) * 0.03)
            igtf_base_maximo = abs(rec.amount_total_usd)
            if content:
                for c in content:
                    account_payment_id = c.get('account_payment_id')
                    payment = self.env['account.payment'].search([('id', '=', account_payment_id)])
                    if payment:
                        igtf_aplicado += payment.mount_igtf
                        igtf_base += payment.amount
            if igtf_aplicado > igtf_maximo:
                igtf_aplicado = igtf_maximo
            if igtf_base > igtf_base_maximo:
                igtf_base = igtf_base_maximo
            rec.igtf_aplicado = igtf_aplicado
            rec.igtf_base = igtf_base

    def _post(self, soft=True):
        res = super(AccountMove, self)._post(soft=soft)
        for rec in self:
           payment_term = rec.line_ids.filtered(lambda l: l.display_type == 'payment_term')
           if payment_term:
               if payment_term.debit > 0:
                   ##print('credit_usd',sum(rec.line_ids.filtered(lambda l: l.credit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('credit_usd')))
                   payment_term.debit_usd = sum(rec.line_ids.filtered(lambda l: l.credit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('credit_usd'))
               elif payment_term.credit > 0:
                   ##print('debit_usd',sum(rec.line_ids.filtered(lambda l: l.debit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('debit_usd')))
                   payment_term.credit_usd = sum(rec.line_ids.filtered(lambda l: l.debit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('debit_usd'))
        for move in self:
            for l in move.line_ids:
                l._onchange_amount_currency()
            move._verificar_pagos()
        return res

    @api.depends('asset_id', 'depreciation_value', 'asset_id.total_depreciable_value', 'asset_id.already_depreciated_amount_import')
    def _compute_depreciation_cumulative_value(self):
        super(AccountMove, self)._compute_depreciation_cumulative_value()
        for move in self:
            if move.asset_id:
                move.asset_remaining_value_ref = (move.asset_remaining_value / move.tax_today) if move.tax_today != 0 else 0
                move.asset_depreciated_value_ref = (move.asset_depreciated_value / move.tax_today) if move.tax_today != 0 else 0

    @api.depends('line_ids.balance_usd')
    def _compute_depreciation_value_ref(self):
        for move in self:
            asset = move.asset_id or move.reversed_entry_id.asset_id  # reversed moves are created before being assigned to the asset
            if asset:
                account_internal_group = 'expense'
                asset_depreciation = sum(
                    move.line_ids.filtered(lambda l: l.account_id.internal_group == account_internal_group or l.account_id == asset.account_depreciation_expense_id).mapped('balance_usd')
                )
                # Special case of closing entry - only disposed assets of type 'purchase' should match this condition
                if any(
                        line.account_id == asset.account_asset_id
                        and float_compare(-line.balance_usd, asset.original_value_ref, precision_rounding=asset.currency_id.rounding) == 0
                        for line in move.line_ids
                ):
                    asset_depreciation = (
                        asset.original_value_ref
                        - asset.salvage_value_ref
                        - (
                            move.line_ids[1].debit_usd if asset.original_value_ref > 0 else move.line_ids[1].credit_usd
                        ) * (-1 if asset.original_value_ref < 0 else 1)
                    )
            else:
                asset_depreciation = 0
            move.depreciation_value_ref = asset_depreciation

    # -------------------------------------------------------------------------
    # INVERSE METHODS
    # -------------------------------------------------------------------------
    def _inverse_depreciation_value(self):
        for move in self:
            asset = move.asset_id
            amount = abs(move.depreciation_value_ref)
            account = asset.account_depreciation_expense_id if asset.asset_type != 'sale' else asset.account_depreciation_id
            move.write({'line_ids': [
                Command.update(line.id, {
                    'balance_usd': amount if line.account_id == account else -amount,
                })
                for line in move.line_ids
            ]})

    def _verificar_pagos(self):
        for rec in self:
            payment_term = rec.line_ids.filtered(lambda l: l.display_type == 'payment_term')
            if payment_term:
                if payment_term.debit > 0:
                    # #print('credit_usd',sum(rec.line_ids.filtered(lambda l: l.credit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('credit_usd')))
                    payment_term.debit_usd = sum(rec.line_ids.filtered(
                        lambda l: l.credit_usd > 0 and l.display_type not in ['payment_term', 'cogs']).mapped(
                        'credit_usd'))
                elif payment_term.credit > 0:
                    # #print('debit_usd',sum(rec.line_ids.filtered(lambda l: l.debit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('debit_usd')))
                    payment_term.credit_usd = sum(rec.line_ids.filtered(
                        lambda l: l.debit_usd > 0 and l.display_type not in ['payment_term', 'cogs']).mapped(
                        'debit_usd'))
            #rec._compute_amount()
            #pass
            for line in rec.line_ids:
                if line.balance_usd == 0:
                    line._compute_balance_usd()
                line._compute_amount_residual_usd()
            rec.verificar_pagos = True

    @api.depends('invoice_date', 'company_id')
    def _compute_date(self):
        res = super(AccountMove, self)._compute_date()
        for rec in self:
            if rec.invoice_date and rec.company_id.currency_id_dif and not rec.tax_today_edited:
                new_rate_ids = self.env.company.currency_id_dif._get_rates(self.env.company, rec.invoice_date)
                if new_rate_ids:
                    new_rate = 1 / new_rate_ids[self.env.company.currency_id_dif.id]
                    rec.tax_today = new_rate
                    # commit
                    self._onchange_tax_today()
                    #self.env.cr.commit()
        # if self.invoice_date and self.company_id.currency_id_dif and not self.tax_today_edited:
        #     new_rate_ids = self.env.company.currency_id_dif._get_rates(self.env.company, self.invoice_date)
        #     if new_rate_ids:
        #         new_rate = 1 / new_rate_ids[self.env.company.currency_id_dif.id]
        #         self.tax_today = new_rate



    @api.model_create_multi
    def create(self, values):
        #verificar si viene asiento de diferencia
        diferencia = False
        line_ids = []
        if 'Diferencia en tasa de cambio' in str(values):
            diferencia = True
        for val in values:
            if 'line_ids' in val:
                if val['line_ids']:
                    for idx, l in enumerate(val['line_ids']):
                        if diferencia:
                            #verifica si el texto l[2]['name'] contiene la palabra diferencia
                            if 'name' in l[2] and 'Diferencia en tasa' in l[2]['name']:
                                #elimina la linea de diferencia
                                val['line_ids'].pop(idx)
                            else:
                                #cambia la moneda a Bs
                                journal_id = self.env['account.journal'].search([('id', '=', val['journal_id'])])
                                company_id = journal_id.company_id
                                l[2]['currency_id'] = company_id.currency_id.id
                                l[2]['debit'] = l[2]['balance'] if l[2]['balance'] > 0 else 0
                                l[2]['credit'] = l[2]['balance'] if l[2]['balance'] < 0 else 0
                                l[2]['partner_id'] = None
                                l[2]['amount_currency'] = l[2]['balance']
                                line_ids.append(l)
            if diferencia:
                val['line_ids'] = line_ids
        if values:
            for val in values:
                if not 'tax_today' in val and not diferencia:
                    module_dual_currency = self.env['ir.module.module'].sudo().search(
                        [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                    if module_dual_currency:
                        val.update({'tax_today': self.env.company.currency_id_dif.inverse_company_rate})
                # elif 'tax_today' in val:
                #     if val['tax_today'] == 0:
                #         module_dual_currency = self.env['ir.module.module'].sudo().search(
                #             [('name', '=', 'account_dual_currency'), ('state', '=', 'installed')])
                #         if module_dual_currency:
                #             val.update({'tax_today': self.env.company.currency_id_dif.tasa_referencia})


        res = super(AccountMove, self).create(values)
        return res

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        #buscar el line_ids lo que no sea payment_term
        # for rec in self:
        #    payment_term = rec.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        #    #print('payment_term', payment_term, payment_term.debit, payment_term.credit, payment_term.debit_usd, payment_term.credit_usd)
        #    if payment_term:
        #        if payment_term.debit > 0:
        #            payment_term.debit_usd = sum(rec.line_ids.filtered(lambda l: l.credit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('credit_usd'))
        #        elif payment_term.credit > 0:
        #            payment_term.credit_usd = sum(rec.line_ids.filtered(lambda l: l.debit_usd > 0 and l.display_type not in ['payment_term','cogs']).mapped('debit_usd'))

        return res

    @api.depends('currency_id')
    def _same_currency(self):
        self.same_currency = self.currency_id == self.env.company.currency_id


    @api.onchange('tax_today')
    def _onchange_tax_today(self):
        self = self.with_context(check_move_validity=False)
        for rec in self:
            self.tax_today_edited = True
            if not rec.move_type == 'entry':
                #es una factura
                #verificar si es una fcatura de proveedor
                if rec.move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                    if rec.currency_id == rec.company_id.currency_id and rec.acuerdo_moneda:
                        for l in rec.invoice_line_ids:
                            l.price_unit_usd = (l.price_unit / rec.tax_today) if rec.currency_id == rec.company_id.currency_id else l.price_unit_usd
                    else:
                        for l in rec.invoice_line_ids:
                            if not rec.acuerdo_moneda:
                                l.price_unit = (l.price_unit_usd * rec.tax_today) if rec.currency_id == rec.company_id.currency_id else l.price_unit_usd

                else:
                    for l in rec.invoice_line_ids:
                        l.price_unit = (l.price_unit_usd * rec.tax_today) if rec.currency_id == rec.company_id.currency_id else l.price_unit_usd

                    rec._onchange_quick_edit_total_amount()
                    rec._onchange_quick_edit_line_ids()

                    rec._compute_tax_totals()

                    #rec.line_ids._compute_currency_rate()
                    #rec.line_ids._compute_amount_currency()

                    #rec.invoice_line_ids._compute_totals()
                    #rec._onchange_tax_today()

            else:
                model_active = self._context.get('active_model')
                for aml in rec.line_ids:
                    if aml.debit_usd > 0:
                        aml.with_context(check_move_validity=False).debit = aml.debit_usd * rec.tax_today
                    elif aml.debit_usd == 0 and aml.debit > 0:
                        aml.with_context(check_move_validity=False).debit_usd = (aml.debit / rec.tax_today) if rec.tax_today > 0 else 0
                    if aml.credit_usd > 0:
                        aml.with_context(check_move_validity=False).credit = aml.credit_usd * rec.tax_today
                    elif aml.credit_usd == 0 and aml.credit > 0:
                        aml.with_context(check_move_validity=False).credit_usd = (aml.credit / rec.tax_today) if rec.tax_today > 0 else 0

    @api.depends('currency_id_dif')
    def _name_ref(self):
        for record in self:
            record.name_rate = record.currency_id_dif.currency_unit_label

    # @api.onchange('currency_id')
    # def _onchange_currency(self):
    #     for rec in self:
    #         #print('cambio de moneda', self.currency_id.name)
    #         if rec.currency_id == rec.company_id.currency_id:
    #             for l in rec.invoice_line_ids:
    #                 # pass
    #                 #l.currency_id = rec.currency_id
    #                 l.price_unit = (l.price_unit_usd * (rec.tax_today if rec.tax_today > 0 else l.price_unit))
    #
    #         else:
    #             for l in rec.invoice_line_ids:
    #                 # pass
    #                 #l.currency_id = rec.currency_id
    #                 l.price_unit = l.price_unit_usd

            #rec.line_ids._compute_all_tax()

            #rec.invoice_line_ids._onchange_price_subtotal()

            #rec._onchange_tax_today()
            #rec._recompute_dynamic_lines(recompute_all_taxes=True)
            #for aml in rec.line_ids:
            #    aml.currency_id = rec.currency_id
                #aml._compute_currency_rate()
                #aml._compute_amount_currency()
                #aml._compute_balance()

            #rec._compute_tax_totals()
            #rec.invoice_line_ids._compute_totals()

    @api.depends('state', 'move_type')
    def _edit_trm(self):
        for rec in self:
            edit_trm = False
            if rec.move_type in ('in_invoice', 'in_refund', 'in_receipt', 'entry'):
                if rec.state == 'draft':
                    edit_trm = True
                else:
                    edit_trm = False
            else:
                edit_trm = self.env.user.has_group('account_dual_currency.group_edit_trm')
                if edit_trm:
                    if rec.state == 'draft':
                        edit_trm = True
                    else:
                        edit_trm = False
            rec.edit_trm = edit_trm

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.balance',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id','tax_today',
        'state')
    def _compute_amount(self):
        for move in self:
            ##print('entra a compute amount')
            if move.currency_id == move.company_id.currency_id:
                for l in move.invoice_line_ids:
                    if not move.acuerdo_moneda:
                        l.price_unit = (l.price_unit_usd * (move.tax_today if move.tax_today > 0 else l.price_unit))
            self.env.context = dict(self.env.context, tasa_factura=move.tax_today, calcular_dual_currency=True)
            super(AccountMove, self)._compute_amount()
            total_residual = 0.0
            total = 0.0
            for line in move.line_ids:
                if move.is_invoice(True):
                    if line.display_type == 'tax' or (line.display_type == 'rounding' and line.tax_repartition_line_id):
                        # Tax amount.
                        total += line.balance_usd
                    elif line.display_type in ('product', 'rounding'):
                        total += line.balance_usd
                    elif line.display_type == 'payment_term':
                        # Residual amount.
                        total_residual += line.amount_residual_usd
                else:
                    # === Miscellaneous journal entry ===
                    if line.debit:
                        total += line.balance_usd
            move.amount_residual_usd = total_residual
            move.amount_total_signed_usd = abs(total) if move.move_type == 'entry' else -total
            self.env.context = dict(self.env.context, tasa_factura=None, calcular_dual_currency=False)

    @api.depends(
        'tax_totals',
        'currency_id_dif',
        'currency_id','tax_today','state', 'invoice_line_ids.price_unit_usd')
    def _amount_all_usd(self):
        for rec in self:
            if rec.is_invoice(include_receipts=True) and rec.tax_totals:
                #rec.line_ids._onchange_amount_currency()
                amount_untaxed = rec.tax_totals['amount_untaxed'] if rec.tax_totals['amount_untaxed'] else 0
                amount_tax = 0
                for product, income in rec.tax_totals['groups_by_subtotal'].items():
                    for l in income:
                        amount_tax += l['tax_group_amount']

                amount_total = rec.tax_totals['amount_total']
                if rec.currency_id != rec.company_id.currency_id:
                    rec.amount_untaxed_usd = rec.amount_untaxed
                    rec.amount_tax_usd = rec.amount_tax
                    rec.amount_total_usd = rec.amount_total
                    rec.amount_untaxed_bs = rec.amount_untaxed_usd * rec.tax_today
                    rec.amount_tax_bs = (rec.amount_tax * rec.tax_today) if rec.amount_tax > 0 else 0
                    rec.amount_total_bs = rec.amount_total_usd * rec.tax_today
                else:
                    rec.amount_untaxed_usd = abs(sum(rec.line_ids.filtered(lambda line: line.display_type == 'product').mapped('balance_usd')))
                    if len(rec.line_ids.filtered(lambda line: line.display_type not in ('product', 'payment_term'))) > 0:
                        rec.amount_tax_usd = abs(sum(rec.line_ids.filtered(lambda line: line.display_type not in ('product', 'payment_term')).mapped('balance_usd')))
                    else:
                        rec.amount_tax_usd = 0
                    rec.amount_total_usd = rec.amount_untaxed_usd + rec.amount_tax_usd
                    rec.amount_untaxed_bs = rec.amount_untaxed
                    rec.amount_tax_bs = rec.amount_tax
                    rec.amount_total_bs = rec.amount_total
            else:
                rec.amount_untaxed_usd = 0
                rec.amount_tax_usd = 0
                rec.amount_total_usd = 0
                rec.amount_untaxed_bs = 0
                rec.amount_tax_bs = 0
                rec.amount_total_bs = 0

    @api.depends('move_type', 'line_ids.amount_residual_usd')
    def _compute_payments_widget_reconciled_info_USD(self):
        for move in self:
            payments_widget_vals = {'title': _('Less Payment'), 'outstanding': False, 'content': []}
            total_pagado = 0
            if move.state == 'posted' and move.is_invoice(include_receipts=True):
                reconciled_vals = []
                reconciled_partials = move._get_all_reconciled_invoice_partials_USD()

                for reconciled_partial in reconciled_partials:
                    counterpart_line = reconciled_partial['aml']
                    if counterpart_line.move_id.ref:
                        reconciliation_ref = '%s (%s)' % (counterpart_line.move_id.name, counterpart_line.move_id.ref)
                    else:
                        reconciliation_ref = counterpart_line.move_id.name
                    if counterpart_line.amount_currency and counterpart_line.currency_id != counterpart_line.company_id.currency_id:
                        foreign_currency = counterpart_line.currency_id
                    else:
                        foreign_currency = False
                    total_pagado = total_pagado + float(reconciled_partial['amount'])
                    reconciled_vals.append({
                        'name': counterpart_line.name,
                        'journal_name': counterpart_line.journal_id.name,
                        'amount': reconciled_partial['amount'],
                        'currency_id': move.company_id.currency_id_dif.id if move.company_id.currency_id_dif else
                        move.company_id.currency_id.id,
                        'date': counterpart_line.date,
                        'partial_id': reconciled_partial['partial_id'],
                        'account_payment_id': counterpart_line.payment_id.id,
                        'payment_method_name': counterpart_line.payment_id.payment_method_line_id.name,
                        'move_id': counterpart_line.move_id.id,
                        'ref': reconciliation_ref,
                        # these are necessary for the views to change depending on the values
                        'is_exchange': reconciled_partial['is_exchange'],
                        'amount_company_currency': formatLang(self.env, abs(counterpart_line.balance_usd),
                                                              currency_obj=counterpart_line.company_id.currency_id_dif),
                        'amount_foreign_currency': foreign_currency and formatLang(self.env,
                                                                                   abs(counterpart_line.amount_currency),
                                                                                   currency_obj=foreign_currency)
                    })
                payments_widget_vals['content'] = reconciled_vals

            if payments_widget_vals['content']:
                move.invoice_payments_widget_usd = payments_widget_vals
                if total_pagado < move.amount_total_usd:
                    move.amount_residual_usd = move.amount_total_usd - total_pagado
                else:
                    move.amount_residual_usd = 0
                # if move.amount_residual_usd > 0:
                #     move.payment_state = 'partial'
                # else:
                #     move.payment_state = 'paid'
            else:
                move.amount_residual_usd = move.amount_total_usd
                move.invoice_payments_widget_usd = False

    @api.depends('move_type', 'line_ids.amount_residual_usd')
    def _compute_payments_widget_reconciled_info_bs(self):
        for move in self:
            if move.state != 'posted' or not move.is_invoice(include_receipts=True):
                move.invoice_payments_widget_bs = json.dumps(False)
                continue
            reconciled_vals = move._get_reconciled_info_JSON_values_bs()
            if reconciled_vals:
                info = {
                    'title': _('Less Payment'),
                    'outstanding': False,
                    'content': reconciled_vals,
                }
                move.invoice_payments_widget_bs = json.dumps(info, default=date_utils.json_default)
            else:
                move.invoice_payments_widget_bs = json.dumps(False)

    def _get_reconciled_info_JSON_values_bs(self):
        self.ensure_one()
        foreign_currency = self.currency_id if self.currency_id != self.company_id.currency_id else False

        reconciled_vals = []
        pay_term_line_ids = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        partials = pay_term_line_ids.mapped('matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
        for partial in partials:
            counterpart_lines = partial.debit_move_id + partial.credit_move_id

            counterpart_line = counterpart_lines.filtered(lambda line: line not in self.line_ids)

            if counterpart_line.credit > 0:
                amount = counterpart_line.credit
            else:
                amount = counterpart_line.debit

            ref = counterpart_line.move_id.name
            if counterpart_line.move_id.ref:
                ref += ' (' + counterpart_line.move_id.ref + ')'

            reconciled_vals.append({
                'name': counterpart_line.name,
                'journal_name': counterpart_line.journal_id.name,
                'amount': partial.amount,
                'currency': self.currency_id_dif.symbol,
                'digits': [69, 2],
                'position': self.currency_id_dif.position,
                'date': counterpart_line.date,
                'payment_id': counterpart_line.id,
                'account_payment_id': counterpart_line.payment_id.id,
                'payment_method_name': counterpart_line.payment_id.payment_method_id.name if counterpart_line.journal_id.type == 'bank' else None,
                'move_id': counterpart_line.move_id.id,
                'ref': ref,
            })
        return reconciled_vals

    def _get_all_reconciled_invoice_partials_USD(self):
        self.ensure_one()
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        if not reconciled_lines:
            return {}

        query = '''
            SELECT
                part.id,
                part.exchange_move_id,
                part.amount_usd AS amount,
                part.credit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.debit_move_id IN %s

            UNION ALL

            SELECT
                part.id,
                part.exchange_move_id,
                part.amount_usd AS amount,
                part.debit_move_id AS counterpart_line_id
            FROM account_partial_reconcile part
            WHERE part.credit_move_id IN %s
        '''
        self._cr.execute(query, [tuple(reconciled_lines.ids)] * 2)

        partial_values_list = []
        counterpart_line_ids = set()
        exchange_move_ids = set()
        for values in self._cr.dictfetchall():
            partial_values_list.append({
                'aml_id': values['counterpart_line_id'],
                'partial_id': values['id'],
                'amount': values['amount'],
                'currency': self.currency_id,
            })
            counterpart_line_ids.add(values['counterpart_line_id'])
            if values['exchange_move_id']:
                exchange_move_ids.add(values['exchange_move_id'])

        if exchange_move_ids:
            query = '''
                SELECT
                    part.id,
                    part.credit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line credit_line ON credit_line.id = part.credit_move_id
                WHERE credit_line.move_id IN %s AND part.debit_move_id IN %s

                UNION ALL

                SELECT
                    part.id,
                    part.debit_move_id AS counterpart_line_id
                FROM account_partial_reconcile part
                JOIN account_move_line debit_line ON debit_line.id = part.debit_move_id
                WHERE debit_line.move_id IN %s AND part.credit_move_id IN %s
            '''
            self._cr.execute(query, [tuple(exchange_move_ids), tuple(counterpart_line_ids)] * 2)

            for values in self._cr.dictfetchall():
                counterpart_line_ids.add(values['counterpart_line_id'])
                partial_values_list.append({
                    'aml_id': values['counterpart_line_id'],
                    'partial_id': values['id'],
                    'currency': self.company_id.currency_id,
                })

        counterpart_lines = {x.id: x for x in self.env['account.move.line'].browse(counterpart_line_ids)}
        for partial_values in partial_values_list:
            partial_values['aml'] = counterpart_lines[partial_values['aml_id']]
            partial_values['is_exchange'] = partial_values['aml'].move_id.id in exchange_move_ids
            if partial_values['is_exchange']:
                partial_values['amount'] = abs(partial_values['aml'].balance_usd)

        return partial_values_list

    def js_assign_outstanding_line(self, line_id):
        lines = super(AccountMove, self).js_assign_outstanding_line(line_id)
        line_ids = self.env['account.move.line'].browse(line_id)
        line_ids._compute_amount_residual_usd()
        return lines

    # def js_assign_outstanding_line(self, line_id):
    #     ''' Called by the 'payment' widget to reconcile a suggested journal item to the present
    #     invoice.
    #
    #     :param line_id: The id of the line to reconcile with the current invoice.
    #     '''
    #     self.ensure_one()
    #     lines = self.env['account.move.line'].browse(line_id)
    #     l = self.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
    #     if abs(lines[0].amount_residual) == 0 and abs(lines[0].amount_residual_usd) > 0:
    #         if l.full_reconcile_id:
    #             l.full_reconcile_id.unlink()
    #         partial = self.env['account.partial.reconcile'].create([{
    #             'amount': 0,
    #             'amount_usd': l.move_id.amount_residual_usd if abs(
    #                 lines[0].amount_residual_usd) > l.move_id.amount_residual_usd else abs(
    #                 lines[0].amount_residual_usd),
    #             'debit_amount_currency': 0,
    #             'credit_amount_currency': 0,
    #             'debit_move_id': l.id,
    #             'credit_move_id': line_id,
    #         }])
    #         p = (lines + l).reconcile()
    #         (lines + l)._compute_amount_residual_usd()
    #         return p
    #     else:
    #         results = (lines + l).reconcile()
    #         if 'partials' in results:
    #             if results['partials'].amount_usd == 0:
    #                 monto_usd = 0
    #                 if abs(lines[0].amount_residual_usd) > 0:
    #
    #                     if abs(lines[0].amount_residual_usd) > self.amount_residual_usd:
    #                         monto_usd = self.amount_residual_usd
    #                     else:
    #                         monto_usd = abs(lines[0].amount_residual_usd)
    #                 results['partials'].write({'amount_usd': monto_usd})
    #                 lines[0]._compute_amount_residual_usd()
    #         return results

    def _compute_payments_widget_to_reconcile_info(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = False
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or not move.is_invoice(include_receipts=True):
                continue
            ##print(move.amount_residual, move.amount_residual_usd)
            if move.payment_state not in ('not_paid', 'partial') and abs(move.amount_residual) == 0 and abs(move.amount_residual_usd) == 0:
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                '|','|', ('amount_residual', '!=', 0.0), ('amount_residual_usd', '!=', 0.0),('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():

                domain.append('|')
                domain.append(('balance', '<', 0.0))
                domain.append(('balance_usd', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:

                domain.append('|')
                domain.append(('balance', '>', 0.0))
                domain.append(('balance_usd', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')
            limit = 5
            if move.move_type in ('in_invoice', 'in_receipt'):
                limit = 200
            ##print('domain', domain)
            for line in self.env['account.move.line'].search(domain,limit=limit):
                line._compute_amount_residual_usd()
                if line.debit == 0 and line.credit == 0 and not line.full_reconcile_id:
                    if abs(line.amount_residual_usd) > 0:
                        payments_widget_vals['content'].append({
                            'journal_name': '%s (%s)' % (line.ref or line.move_id.name, line.currency_id.name),
                            'amount': 0,
                            'amount_usd': round(abs(line.amount_residual_usd), line.company_id.currency_id_dif.decimal_places),
                            'currency_id': move.company_id.currency_id.id,
                            'currency_id_dif': move.currency_id_dif.id,
                            'id': line.id,
                            'move_id': line.move_id.id,
                            'date': fields.Date.to_string(line.date),
                            'account_payment_id': line.payment_id.id,
                        })
                        continue
                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual)
                    amount_usd = abs(line.amount_residual_usd)
                else:
                    # Different foreign currencies.
                    # amount = line.company_currency_id._convert(
                    #     abs(line.amount_residual),
                    #     move.currency_id,
                    #     move.company_id,
                    #     line.date,
                    # )
                    amount = abs(line.amount_residual)
                    amount_usd = abs(line.amount_residual_usd)

                if move.currency_id.is_zero(amount) and amount_usd == 0:
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': '%s (%s)' % (line.ref or line.move_id.name, line.currency_id.name),
                    'amount': amount,
                    'amount_usd': round(amount_usd, line.company_id.currency_id_dif.decimal_places),
                    'currency_id': move.company_id.currency_id.id,
                    'currency_id_dif': move.currency_id_dif.id,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'date': fields.Date.to_string(line.date),
                    'account_payment_id': line.payment_id.id,
                })

            if not payments_widget_vals['content']:
                continue
            move.invoice_outstanding_credits_debits_widget = payments_widget_vals
            move.invoice_has_outstanding = True

    @api.model
    def _prepare_move_for_asset_depreciation(self, vals):
        move_vals = super(AccountMove, self)._prepare_move_for_asset_depreciation(vals)
        asset_id = vals.get('asset_id')
        move_vals['tax_today'] = asset_id.tax_today
        move_vals['currency_id_dif'] = asset_id.currency_id_dif.id
        #move_vals['asset_remaining_value_ref'] = move_vals['asset_remaining_value'] / asset_id.tax_today
        #move_vals['asset_depreciated_value_ref'] = move_vals['asset_depreciated_value'] / asset_id.tax_today
        return move_vals

    def js_remove_outstanding_partial(self, partial_id):
        ''' Called by the 'payment' widget to remove a reconciled entry to the present invoice.

        :param partial_id: The id of an existing partial reconciled with the current invoice.
        '''
        self.ensure_one()
        partial = self.env['account.partial.reconcile'].browse(partial_id)
        debit_move_id = partial.debit_move_id
        credit_move_id = partial.credit_move_id
        res = partial.unlink()
        if debit_move_id and credit_move_id:
            debit_move_id._compute_amount_residual_usd()
            credit_move_id._compute_amount_residual_usd()
        return res

    def generar_retencion_igtf(self):
        for rec in self:
            return {'name': _('Aplicar Retención IGTF'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'generar.igtf.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                    'domain': "",
                    'context': {
                            'default_invoice_id': rec.id,
                            'default_igtf_porcentage': rec.company_id.igtf_divisa_porcentage,
                            'default_tax_today': rec.currency_id_dif.inverse_company_rate,
                            'default_currency_id_dif': rec.currency_id_dif.id,
                            'default_currency_id_company': rec.company_id.currency_id.id,
                            'default_amount': rec.amount_residual_usd,
                        },
                    }

    def button_create_landed_costs(self):
        """Create a `stock.landed.cost` record associated to the account move of `self`, each
        `stock.landed.costs` lines mirroring the current `account.move.line` of self.
        """
        self.ensure_one()
        landed_costs_lines = self.line_ids.filtered(lambda line: line.is_landed_costs_line)
        cost_lines = [(0, 0, {
                'product_id': l.product_id.id,
                'name': l.product_id.name,
                'account_id': l.product_id.property_account_expense_id.id or l.product_id.product_tmpl_id.get_product_accounts()['stock_input'].id,
                'tax_today': l.tax_today,
                'currency_price_unit': l.price_unit if l.currency_id == self.company_id.currency_id else l.price_unit_usd,
                'price_unit': l.currency_id._convert(l.price_subtotal, l.company_currency_id, l.company_id, self.invoice_date),
                'split_method': l.product_id.split_method_landed_cost or 'equal',
            }) for l in landed_costs_lines]
        landed_costs = self.env['stock.landed.cost'].with_company(self.company_id).create({
            'vendor_bill_id': self.id,
            'cost_lines': cost_lines,
        })
        action = self.env["ir.actions.actions"]._for_xml_id("stock_landed_costs.action_stock_landed_cost")
        return dict(action, view_mode='form', res_id=landed_costs.id, views=[(False, 'form')])

    def _reverse_moves(self, default_values_list=None, cancel=False):
        ''' Reverse a recordset of account.move.
        If cancel parameter is true, the reconcilable or liquidity lines
        of each original move will be reconciled with its reverse's.
        :param default_values_list: A list of default values to consider per move.
                                    ('type' & 'reversed_entry_id' are computed in the method).
        :return:                    An account.move recordset, reverse of the current self.
        '''
        if not default_values_list:
            default_values_list = [{} for move in self]

        if cancel:
            lines = self.mapped('line_ids')
            ##print('lines', lines)
            # Avoid maximum recursion depth.
            if lines:
                lines.remove_move_reconcile()
            ##print('lines', lines)
        reverse_moves = self.env['account.move']
        for move, default_values in zip(self, default_values_list):
            default_values.update({
                'move_type': TYPE_REVERSE_MAP[move.move_type],
                'reversed_entry_id': move.id,
                'reversed_entry_id_new': move.id,
                'partner_id': move.partner_id.id,
            })
            reverse_moves += move.with_context(
                move_reverse_cancel=cancel,
                include_business_fields=True,
                skip_invoice_sync=move.move_type == 'entry',
            ).copy(default_values)

        reverse_moves.with_context(skip_invoice_sync=cancel).write({'line_ids': [
            Command.update(line.id, {
                'balance': -line.balance,
                'amount_currency': -line.amount_currency,
                'debit_usd': line.credit_usd,
                'credit_usd': line.debit_usd,
            })
            for line in reverse_moves.line_ids
            if line.move_id.move_type == 'entry' or line.display_type == 'cogs'
        ]})

        #agregar cogs a la inversa si existen
        # if self.line_ids.filtered(lambda l: l.display_type == 'cogs'):
        #     reverse_moves.with_context(skip_invoice_sync=cancel).write({'line_ids': [
        #         Command.create({
        #             'name': l.name,
        #             'account_id': l.account_id.id,
        #             'debit': l.credit,
        #             'credit': l.debit,
        #             'display_type': l.display_type,
        #             'quantity': l.quantity,
        #             'product_id': l.product_id.id,
        #             'product_uom_id': l.product_uom_id.id,
        #             'tax_ids': [(6, 0, l.tax_ids.ids)],
        #             'analytic_distribution': l.analytic_distribution,
        #         })
        #         for l in self.line_ids.filtered(lambda l: l.display_type == 'cogs')
        #     ]})

        # Reconcile moves together to cancel the previous one.
        if cancel:
            reverse_moves.with_context(move_reverse_cancel=cancel)._post(soft=False)

        return reverse_moves

    def close_invoice(self):
        for rec in self:
            company_id = rec.company_id if not rec.company_id.parent_id else rec.company_id.parent_id
            if company_id.automatic_closing and rec.move_type in ('out_invoice', 'in_invoice'):
                generate_move = False
                #verifica el residual $ es menor o igual a
                if rec.amount_residual_usd <= company_id.closing_tolerance_usd:
                    #verifica el porcentaje que representa el residual $ sobre el total
                    porc = (rec.amount_residual_usd / rec.amount_total_usd) * 100
                    if porc <= company_id.closing_tolerance_porc:
                        generate_move = True

                print('rec.amount_residual_usd', rec.amount_residual_usd, 'generate_move', generate_move)
                if generate_move:
                    line_factura = rec.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
                    line_ids = []
                    #apunte de contrapartida para conciliar con la facturas, debe ser a la misma cuenta por cobrar de la factura
                    line_ids.append((0, 0, {
                        'name': 'Cierre de Factura ' + rec.name,
                        'account_id': rec.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable').account_id.id,
                        'partner_id': rec.partner_id.id,
                        'credit': rec.amount_residual,
                        'credit_usd': rec.amount_residual_usd,
                        'debit': 0,
                        'debit_usd': 0,
                        'no_calcular': True,
                    }))
                    #apunte de contrapartida para perdida
                    line_ids.append((0, 0, {
                        'name': 'Cierre de Factura ' + rec.name,
                        'account_id': company_id.closing_account_id.id,
                        'debit': rec.amount_residual,
                        'debit_usd': rec.amount_residual_usd,
                        'credit': 0,
                        'credit_usd': 0,
                        'no_calcular': True,
                    }))
                    move = {
                        'move_type': 'entry',
                        'journal_id': company_id.closing_journal_id.id,
                        'date': fields.Date.today(),
                        'tax_today': rec.tax_today,
                        'ref': 'Cierre de Factura ' + rec.name,
                        'line_ids': line_ids,
                    }
                    move_id = self.create(move)
                    move_id._post()
                    #conciliar la factura con el apunte de cierre
                    line_move = move_id.line_ids.filtered(lambda l: l.account_id == line_factura.account_id)
                    (line_factura + line_move).reconcile()







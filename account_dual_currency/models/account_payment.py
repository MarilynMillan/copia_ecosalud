# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _name = 'account.payment'
    _inherit = ['account.payment', 'mail.thread', 'mail.activity.mixin', 'portal.mixin', 'analytic.mixin']

    tax_today = fields.Float(string="Tasa", default=lambda self: self._get_default_tasa(), digits='Dual_Currency_rate')
    currency_id_dif = fields.Many2one("res.currency",
                                      string="Divisa de Referencia",
                                      default=lambda self: self.env.company.currency_id_dif )
    currency_id_company = fields.Many2one("res.currency",
                                          string="Divisa compañia",
                                          default=lambda self: self.env.company.currency_id)
    amount_local = fields.Monetary(string="Importe local", currency_field='currency_id_company')
    amount_ref = fields.Monetary(string="Importe referencia", currency_field='currency_id_dif')
    currency_equal = fields.Boolean(compute="_currency_equal")
    move_id_dif = fields.Many2one(
        'account.move', 'Asiento contable diferencia',  # required=True,
        readonly=True,
        help="Asiento contable de diferencia en tipo de cambio")

    currency_id_name = fields.Char(related="currency_id.name")
    journal_igtf_id = fields.Many2one('account.journal', string='Diario IGTF', check_company=True)
    aplicar_igtf_divisa = fields.Boolean(string="Aplicar IGTF")
    igtf_divisa_porcentage = fields.Float('% IGTF', related='company_id.igtf_divisa_porcentage')

    mount_igtf = fields.Monetary(currency_field='currency_id', string='Importe IGTF', readonly=True,
                                 digits='Dual_Currency')

    amount_total_pagar = fields.Monetary(currency_field='currency_id', string="Total Pagar(Importe + IGTF):",
                                         readonly=True)

    move_id_igtf_divisa = fields.Many2one(
        'account.move', 'Asiento IGTF Divisa',
        readonly=True)
    invoices = fields.Many2many('account.move', string="Factura(s)", compute='_compute_invoices', )
    invoice_ids = fields.Many2many('account.move', string="Factura(s)", domain="[('id', 'in', invoices)]")
    amount_total_usd = fields.Monetary(string='Total Facturas $', currency_field='currency_id_dif',
                                       compute='_compute_amount_total', store=True)
    amount_total_bs = fields.Monetary(string='Total Facturas Bs', compute='_compute_amount_total',
                                      currency_field='currency_id_company', store=True)
    amount_diferential = fields.Monetary(string='Diferencial Bs', compute='_compute_amount_diferential',
                                         currency_field='currency_id_company', store=True, help="Diferencia entre el monto total del pago y el monto total de las facturas")

    mantener_bs = fields.Boolean(string="Mantener Bs", default=False)
    related_payment_reference = fields.Char(string='Referencia de Recibir')
    related_date = fields.Date(string='related date')

    diferencial_move_ids = fields.Many2many('account.move', 'diferencial_payment_rel', 'payment_id', 'move_id',
                                            string='Asientos de diferencial', readonly=True, copy=False)

    diferencial_move_count = fields.Integer(compute='_compute_diferencial_move_count', string='Asientos de diferencial')

    @api.depends('diferencial_move_ids')
    def _compute_diferencial_move_count(self):
        for rec in self:
            rec.diferencial_move_count = len(rec.diferencial_move_ids)

    def button_open_diferencial(self):
        self.ensure_one()

        action = {
            'name': _("Asientos de diferencial"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if len(self.diferencial_move_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.diferencial_move_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.diferencial_move_ids.ids)],
            })
        return action

    def write(self, vals):
        res = super().write(vals)
        if 'tax_today' in vals:
            for rec in self:
                rec._currency_equal()
        return res

    @api.depends('partner_id', 'payment_type')
    def _compute_invoices(self):
        for rec in self:
            invoices = False
            if rec.partner_id:
                domain = []
                if rec.payment_type == 'inbound':
                    domain = [('partner_id', '=', rec.partner_id.id), ('move_type', '=', 'out_invoice'),
                              ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]
                elif rec.payment_type == 'outbound':
                    domain = [('partner_id', '=', rec.partner_id.id), ('move_type', '=', 'in_invoice'),
                              ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial'])]
                invoices = self.env['account.move'].search(domain).sorted(key=lambda r: r.date).ids
            rec.invoices = invoices


    @api.depends('invoice_ids','state','diferencial_move_ids')
    def _compute_amount_total(self):
        for rec in self:
            if rec.state == 'draft':
                if rec.invoice_ids:
                    rec.invoice_ids.line_ids._compute_amount_residual_usd()
                    amount_total_usd = abs(sum(rec.invoice_ids.mapped('amount_residual_usd')))
                    amount_total_bs = abs(sum(rec.invoice_ids.mapped('amount_residual_signed')))
                    ##print("amount_total_usd", amount_total_usd)
                    ##print("amount_total_bs", amount_total_bs)
                    rec.amount_total_usd = amount_total_usd
                    rec.amount_total_bs = amount_total_bs
                    #rec.amount = rec.amount_total_usd if rec.currency_id.id == rec.currency_id_dif.id else rec.amount_total_usd * rec.tax_today
                else:
                    rec.amount_total_usd = 0
                    rec.amount_total_bs = 0

                rec._compute_amount_diferential()

    @api.depends('invoice_ids', 'amount_local', 'amount_total_bs')
    def _compute_amount_diferential(self):
        for rec in self:
            rec.amount_diferential = 0
            if len(rec.invoice_ids) >= 1:
                rec.amount_diferential = rec.amount_local - rec.amount_total_bs

    def _get_default_tasa(self):
        return self.env.company.currency_id_dif.inverse_company_rate

    @api.depends('currency_id_dif','currency_id','amount','tax_today')
    def _currency_equal(self):
        for rec in self:
            rec._compute_amount_total()
            currency_equal = rec.currency_id_company != rec.currency_id
            if rec.state == 'draft':
                if currency_equal:
                    rec.amount_local = (rec.amount * rec.tax_today) if not rec.paired_internal_transfer_payment_id else rec.paired_internal_transfer_payment_id.amount
                    rec.amount_ref = rec.amount
                else:
                    #obtener el modelo activo
                    active_model = self._context.get('active_model')
                    if not active_model:
                        if rec.mantener_bs:
                            rec.amount_local = rec.amount
                            rec.amount_ref = (rec.amount / rec.tax_today) if rec.amount > 0 and rec.tax_today > 0 else 0
                        else:
                            if rec.amount_ref > 0:
                                rec.amount = (rec.amount_ref * rec.tax_today)
                            else:
                                rec.amount_ref = (rec.amount / rec.tax_today) if rec.amount > 0 and rec.tax_today > 0 else 0
                    else:
                        rec.amount_local = rec.amount
                        rec.amount_ref = (rec.amount / rec.tax_today) if rec.amount > 0 and rec.tax_today > 0 else 0



                if rec.aplicar_igtf_divisa:
                    if rec.currency_id.name == 'USD':
                        rec.mount_igtf = rec.amount * rec.igtf_divisa_porcentage / 100
                        rec.amount_total_pagar = rec.mount_igtf + rec.amount
                    else:
                        rec.mount_igtf = 0
                        rec.amount_total_pagar = rec.amount
                else:
                    rec.mount_igtf = 0
                    rec.amount_total_pagar = rec.amount

            rec.currency_equal = currency_equal

    def action_draft(self):
        ''' posted -> draft '''
        self.move_id_dif.button_draft()
        if self.move_id_igtf_divisa:
            if self.move_id_igtf_divisa.state == 'done':
                self.move_id_igtf_divisa.button_draft()
        for rec in self:
            if rec.diferencial_move_ids:
                diferencial_move_ids = rec.diferencial_move_ids.filtered(lambda r: r.state == 'posted')
                if diferencial_move_ids:
                    diferencial_move_ids.button_draft()
                    diferencial_move_ids.button_cancel()
        res = super().action_draft()

    def action_cancel(self):
        ''' draft -> cancelled '''
        res = super().action_cancel()
        self.move_id_dif.button_cancel()
        if self.move_id_igtf_divisa:
            self.move_id_igtf_divisa.button_cancel()

    def action_post(self):
        res = super().action_post()
        self._currency_equal()
        #agregar las analytic_distribution al asiento contable

        ''' draft -> posted '''
        self.move_id_dif._post(soft=False)
        if self.move_id_dif:
            self.move_id_dif.line_ids.analytic_distribution = self.analytic_distribution
        """Genera la retencion IGTF """
        for pago in self:
            pago.move_id.line_ids.analytic_distribution = pago.analytic_distribution
            if not pago.move_id_igtf_divisa:
                if pago.aplicar_igtf_divisa:
                    pago.register_move_igtf_divisa_payment()
            else:
                if pago.move_id_igtf_divisa.state == 'draft':
                    pago.move_id_igtf_divisa.action_post()
            if pago.move_id_igtf_divisa:
                pago.move_id_igtf_divisa.line_ids.analytic_distribution = pago.analytic_distribution
            #si tiene factuas asociadas en self.invoice_ids cruzar el pago con esas facturas
            if self.invoice_ids:
                self._reconcile_invoice_payment()

        return res

    def _reconcile_invoice_payment(self):
        '''Este método realiza la conciliación de las facturas seleccionadas con el pago'''
        for rec in self:
            for invoice in rec.invoice_ids:
                if invoice.state == 'posted':
                    if rec.payment_type == 'inbound':
                        rec._reconcile_invoice_payment_inbound(invoice)
                    elif rec.payment_type == 'outbound':
                        rec._reconcile_invoice_payment_outbound(invoice)
                else:
                    raise UserError(_("La factura %s no esta en estado publicado") % invoice.name)

    def _reconcile_invoice_payment_inbound(self, invoice):
        '''Este método realiza la conciliación de las facturas seleccionadas con el pago'''
        for rec in self:
            if invoice.state == 'posted':
                if invoice.amount_residual_signed > 0:
                    line_invoice = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                    line_payment = rec.move_id.line_ids.filtered(lambda l: l.account_id == line_invoice.account_id)
                    (line_invoice + line_payment).reconcile()

    def _reconcile_invoice_payment_outbound(self, invoice):
        '''Este método realiza la conciliación de las facturas seleccionadas con el pago'''
        for rec in self:
            if invoice.state == 'posted':
                if invoice.amount_residual_signed < 0:
                    line_invoice = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                    line_payment = rec.move_id.line_ids.filtered(lambda l: l.account_id == line_invoice.account_id)
                    (line_invoice + line_payment).reconcile()


    def register_move_igtf_divisa_payment(self):
        '''Este método realiza el asiento contable de la comisión según el porcentaje que indica la compañia'''
        #self.env['ir.sequence'].with_context(ir_sequence_date=self.date_advance).next_by_code(sequence_code)
        diario = self.journal_igtf_id or self.journal_id
        vals = {
            'date': self.date,
            'journal_id': diario.id,
            'currency_id': self.currency_id.id,
            'state': 'draft',
            'tax_today':self.tax_today,
            'ref':self.ref,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                'account_id': diario.suspense_account_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'date_maturity': False,
                'ref': "Comisión IGTF Divisa",
                'date': self.date,
                'partner_id': self.partner_id.id,
                'name': "Comisión IGTF Divisa",
                'journal_id': self.journal_id.id,
                'credit': float(self.mount_igtf * self.tax_today) if not self.payment_type == 'inbound' else float(0.0),
                'debit': float(self.mount_igtf * self.tax_today) if self.payment_type == 'inbound' else float(0.0),
                'amount_currency': -self.mount_igtf if not self.payment_type == 'inbound' else self.mount_igtf,
            }),
                (0, 0, {
                'account_id': self.company_id.account_debit_wh_igtf_id.id if self.payment_type == 'inbound' else self.company_id.account_credit_wh_igtf_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
                'date_maturity': False,
                'ref': "Comisión IGTF Divisa",
                'date': self.date,
                'name': "Comisión IGTF Divisa",
                'journal_id': self.journal_id.id,
                'credit': float(self.mount_igtf * self.tax_today) if self.payment_type == 'inbound' else float(0.0),
                'debit': float(self.mount_igtf * self.tax_today) if not self.payment_type == 'inbound' else float(0.0),
                'amount_currency': -self.mount_igtf if self.payment_type == 'inbound' else self.mount_igtf,
            }),
            ],
        }


        move_id = self.env['account.move'].with_context(check_move_validity=False).create(vals)

        if move_id:
            res = {'move_id_igtf_divisa': move_id.id}
            self.write(res)
            move_id.action_post()
        return True

    def _prepare_move_line_default_vals(self, write_off_line_vals=None, force_balance=None):
        res = super()._prepare_move_line_default_vals(write_off_line_vals)
        total_debit = 0
        total_credit = 0
        if res:
            currency_id = res[0]['currency_id']
        currencies_are_different = self.currency_id_company.id != currency_id
        for line in res:
            if line['account_id'] == self.outstanding_account_id.id:
                line['tax_today'] = self.tax_today
                if currencies_are_different:
                    line['debit'] = (line['amount_currency'] * self.tax_today) if line['debit'] else 0
                    line['credit'] = (abs(line['amount_currency']) * self.tax_today) if line['credit'] else 0
            elif line['account_id'] == self.destination_account_id.id:
                tasa_factura = self.env.context.get('tasa_factura', self.tax_today)
                line['tax_today'] = tasa_factura if write_off_line_vals else self.tax_today
                if currencies_are_different:
                    line['debit'] = (line['amount_currency'] * line['tax_today']) if line['debit'] else 0
                    line['credit'] = (abs(line['amount_currency']) * line['tax_today']) if line['credit'] else 0
            else:
                continue
            total_debit += line['debit']
            total_credit += line['credit']

        payment_difference_handling = self._context.get('payment_difference_handling', False)
        if currencies_are_different and payment_difference_handling == 'open' and total_debit != total_credit:
            if self.payment_type == 'inbound':
                # Receive money.
                write_off = sum(x['credit'] for x in write_off_line_vals)
                liquidy = sum(x['debit'] for x in res if x['account_id'] == self.outstanding_account_id.id)
            if self.payment_type == 'outbound':
                # Send money.
                write_off = sum(x['debit'] for x in write_off_line_vals)
                liquidy = sum(x['credit'] for x in res if x['account_id'] == self.outstanding_account_id.id)
            counterpart = liquidy - write_off
            for r in res:
                if r['account_id'] == self.destination_account_id.id:
                    if self.payment_type == 'inbound':
                        r['credit'] = counterpart
                        r['balance'] = -counterpart
                    if self.payment_type == 'outbound':
                        r['debit'] = counterpart
                        r['balance'] = counterpart
        return res

    @api.model
    def _get_trigger_fields_to_synchronize(self):
        return (
            'date', 'amount', 'payment_type', 'partner_type', 'payment_reference', 'is_internal_transfer',
            'currency_id', 'partner_id', 'destination_account_id', 'partner_bank_id', 'journal_id', 'tax_today'
        )

    def _synchronize_to_moves(self, changed_fields):
        if 'tax_today' in changed_fields:
            for pay in self.with_context(skip_account_move_synchronization=True):
                pay.move_id.write({
                    'tax_today': pay.tax_today,
                })
        super(AccountMove, self)._synchronize_to_moves(changed_fields)

    def _create_paired_internal_transfer_payment(self):
        ''' When an internal transfer is posted, a paired payment is created
        with opposite payment_type and swapped journal_id & destination_journal_id.
        Both payments liquidity transfer lines are then reconciled.
        '''
        for payment in self:
            mantener_bs = False
            if payment.destination_journal_id.currency_id:
                if payment.destination_journal_id.currency_id == payment.company_id.currency_id:
                    mantener_bs = True
            else:
                mantener_bs = True
            paired_payment = payment.copy({
                'journal_id': payment.destination_journal_id.id,
                'currency_id': payment.destination_journal_id.currency_id.id or payment.company_id.currency_id.id,
                'destination_journal_id': payment.journal_id.id,
                'payment_type': payment.payment_type == 'outbound' and 'inbound' or 'outbound',
                'move_id': None,
                'ref': payment.ref,
                'paired_internal_transfer_payment_id': payment.id,
                'date': payment.related_date if payment.related_date else payment.date,
                'mantener_bs': mantener_bs,
                'related_payment_reference':payment.related_payment_reference
            })
            if payment.journal_id.currency_id == payment.destination_journal_id.currency_id and payment.currency_id == payment.company_id.currency_id:
                paired_payment.amount = payment.amount
            else:
                if payment.currency_id != payment.destination_journal_id.currency_id and payment.currency_id == payment.company_id.currency_id:
                    paired_payment.amount = payment.amount_ref
                    paired_payment.amount_local = payment.amount
                    (paired_payment.move_id.line_ids.with_context(check_move_validity=False)
                     .filtered(lambda l: l.debit > 0).write({'debit': payment.amount}))
                    (paired_payment.move_id.line_ids.with_context(check_move_validity=False)
                     .filtered(lambda l: l.credit > 0).write({'credit': payment.amount}))

                elif payment.currency_id != payment.destination_journal_id.currency_id and payment.currency_id != payment.company_id.currency_id:
                    paired_payment.amount = payment.amount_local

            paired_payment.move_id._post(soft=False)
            payment.paired_internal_transfer_payment_id = paired_payment
            body = _("Este pago ha sido creado a partir de:") + payment._get_html_link()
            paired_payment.message_post(body=body)
            body = _("Se ha creado un segundo pago:") + paired_payment._get_html_link()
            payment.message_post(body=body)

            lines = (payment.move_id.line_ids + paired_payment.move_id.line_ids).filtered(
                lambda l: l.account_id == payment.destination_account_id and not l.reconciled)
            lines.reconcile()

    def crear_diferencial_cambio(self):
        '''Este método realiza el asiento contable de la diferencia en el tipo de cambio'''
        for rec in self:
            if not rec.move_id_dif:
                if rec.amount_diferential != 0:
                    rec.register_move_diferencial_cambio_payment()
            else:
                if rec.move_id_dif.state == 'draft':
                    rec.move_id_dif.action_post()

    def register_move_diferencial_cambio_payment(self):
        '''Este método realiza el asiento contable de la diferencia en el tipo de cambio'''
        vals = {
            'date': self.date,
            'journal_id': self.company_id.currency_exchange_journal_id.id,
            'currency_id': self.company_id.currency_id.id,
            'state': 'draft',
            'tax_today':0,
            'ref':self.ref,
            'move_type': 'entry',
            'line_ids': [
                (0, 0, {
                'account_id': self.company_id.income_currency_exchange_account_id.id if self.amount_diferential > 0 else self.company_id.expense_currency_exchange_account_id.id,
                'ref': "Diferencial Cambio",
                'name': "Diferencial Cambio",
                'journal_id': self.journal_id.id,
                'credit': float(self.amount_diferential) if self.amount_diferential > 0 else 0,
                'debit': float(self.amount_diferential) if self.amount_diferential < 0 else 0,
            }),
                (0, 0, {
                'account_id': self.destination_account_id.id,
                'ref': "Diferencial Cambio",
                'partner_id': self.partner_id.id,
                'name': "Diferencial Cambio",
                'journal_id': self.journal_id.id,
                'credit': float(self.amount_diferential) if self.amount_diferential < 0 else 0,
                'debit': float(self.amount_diferential) if self.amount_diferential > 0 else 0,
            }),
            ],
        }

        move_id = self.env['account.move'].with_context(check_move_validity=False).create(vals)

        if move_id:
            res = {'move_id_dif': move_id.id}
            self.write(res)
            move_id.action_post()
        return True


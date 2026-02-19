# -*- coding: utf-8 -*-
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, timedelta
from functools import lru_cache

from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import frozendict, formatLang, format_date, float_compare, Query
from odoo.tools.float_utils import float_compare, float_is_zero
from odoo.tools import float_round


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    debit_usd = fields.Monetary(currency_field='currency_id_dif', string='Débito $', store=True, compute="_debit_usd",
                                 readonly=False, precompute=True)
    credit_usd = fields.Monetary(currency_field='currency_id_dif', string='Crédito $', store=True,
                                 compute="_credit_usd", readonly=False, precompute=True)
    tax_today = fields.Float(related="move_id.tax_today", store=True, digits='Dual_Currency_rate')
    currency_id_dif = fields.Many2one("res.currency", related="move_id.currency_id_dif", store=True)
    price_unit_usd = fields.Float(currency_field='currency_id_dif', string='Precio $', store=True, digits='Product_Price_USD',
                                     compute='_price_unit_usd', readonly=False, inverse='_inverse_price_unit_usd')
    price_subtotal_usd = fields.Float(currency_field='currency_id_dif', string='SubTotal $', store=True,
                                         compute="_price_subtotal_usd", digits='Product_Price_USD')
    amount_residual_usd = fields.Monetary(string='Residual Amount USD', computed='_compute_amount_residual_usd', store=True,
                                       help="The residual amount on a journal item expressed in the company currency.", currency_field='currency_id_dif')
    balance_usd = fields.Monetary(string='Balance Ref.',
                                  currency_field='currency_id_dif', store=True, readonly=False,
                                  compute='_compute_balance_usd',
                                  default=lambda self: self._compute_balance_usd(),
                                  help="Technical field holding the debit_usd - credit_usd in order to open meaningful graph views from reports")
    no_calcular = fields.Boolean(string="No calcular", default=False)



    @api.depends('currency_id', 'company_id', 'move_id.date','move_id.tax_today')
    def _compute_currency_rate(self):

        @lru_cache()
        def get_rate(from_currency, to_currency, company, date):
            rate = self.env['res.currency']._get_conversion_rate(
                from_currency=from_currency,
                to_currency=to_currency,
                company=company,
                date=date,
            )

            return rate

        for line in self:
            self.env.context = dict(self.env.context, tasa_factura=line.move_id.tax_today, calcular_dual_currency=True)
            # line.currency_rate = get_rate(
            #     from_currency=line.company_currency_id,
            #     to_currency=line.currency_id,
            #     company=line.company_id,
            #     date=line.move_id.invoice_date or line.move_id.date or fields.Date.context_today(line),
            # )
            if line.move_id.currency_id == line.company_id.currency_id:
                line.currency_rate = 1
            else:
                line.currency_rate = 1 / line.move_id.tax_today if line.move_id.tax_today > 0 else 1
        self.env.context = dict(self.env.context, tasa_factura=None, calcular_dual_currency=False)

    @api.onchange('amount_currency')
    def _onchange_amount_currency(self):
        #####print('si entra _onchange_amount_currency')
        if not self.no_calcular:
            self._debit_usd()
            self._credit_usd()

    @api.onchange('price_unit_usd')
    def _onchange_price_unit_usd(self):
        for rec in self:
            if rec.move_id.currency_id != rec.company_id.currency_id:
                rec.price_unit = rec.price_unit_usd
            else:
                if rec.move_id.move_type not in ['in_invoice', 'in_refund']:
                    #####print('si entra')
                    rec.price_unit = rec.price_unit_usd * rec.tax_today


    @api.onchange('product_id')
    def _onchange_product_id(self):
        #super()._onchange_product_id()
        self._price_unit_usd()

    @api.depends('debit_usd', 'credit_usd')
    def _compute_balance_usd(self):
        for line in self:
            line.balance_usd = line.debit_usd - line.credit_usd


    @api.depends('price_unit', 'product_id')
    def _price_unit_usd(self):
        for rec in self:
            if rec.price_unit > 0:
                if rec.move_id.currency_id == rec.company_id.currency_id:
                    rec.price_unit_usd = (rec.price_unit / rec.tax_today) if rec.tax_today > 0 else 0
                else:
                    rec.price_unit_usd = rec.price_unit
            else:
                rec.price_unit_usd = 0

            # if rec.price_unit_usd > 0:
            #     if rec.move_id.currency_id == self.env.company.currency_id:
            #         rec.price_unit = rec.price_unit_usd * rec.tax_today
            #     else:
            #         rec.price_unit = rec.price_unit_usd
            # else:
            #     rec.price_unit = 0

    def _inverse_price_unit_usd(self):
        for rec in self:
            if not rec.move_id.acuerdo_moneda and rec.move_id.move_type in ['in_invoice', 'in_refund']:
                if rec.move_id.currency_id == rec.company_id.currency_id:
                    rec.price_unit = rec.price_unit_usd * rec.tax_today
                else:
                    rec.price_unit = rec.price_unit_usd

    @api.depends('price_unit_usd', 'quantity', 'discount')
    def _price_subtotal_usd(self):
        for line in self:
            line_discount_price_unit = line.price_unit_usd * (1 - (line.discount / 100.0))
            subtotal = line.quantity * line_discount_price_unit


            line.price_subtotal_usd = subtotal
            # if rec.price_subtotal > 0:
            #     if rec.move_id.currency_id == self.env.company.currency_id:
            #         rec.price_subtotal_usd = (rec.price_subtotal / rec.tax_today) if rec.tax_today > 0 else 0
            #     else:
            #         rec.price_subtotal_usd = rec.price_subtotal
            # else:
            #     rec.price_subtotal_usd = 0

            # if rec.price_subtotal_usd > 0:
            #     if rec.move_id.currency_id == self.env.company.currency_id:
            #         rec.price_subtotal = rec.price_subtotal_usd * rec.tax_today
            #     else:
            #         rec.price_subtotal = rec.price_subtotal_usd
            # else:
            #     rec.price_subtotal = 0

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        if 'tax_today' not in fields:
            return super(AccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                           orderby=orderby, lazy=lazy)
        res = super(AccountMoveLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                      orderby=orderby, lazy=lazy)
        for group in res:
            if group.get('__domain'):
                records = self.search(group['__domain'])
                group['tax_today'] = 0
        return res

    @api.depends('amount_currency', 'tax_today','debit','move_id.currency_id')
    def _debit_usd(self):

        for rec in self:
            if not rec.debit == 0 and rec.display_type not in ['line_section', 'line_note']:
                if not rec.no_calcular:
                    if rec.display_type == 'cogs':
                        #calcular el costo de venta en $
                        rec.debit_usd = float_round(rec.product_id.standard_price_usd * rec.quantity, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                    else:
                        if rec.move_id.currency_id == rec.company_id.currency_id:
                            if rec.display_type == 'product' and rec.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                                rec.debit_usd = float_round(rec.price_subtotal_usd, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                            else:
                                amount_currency = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))
                                rec.debit_usd = float_round((amount_currency / rec.tax_today) if rec.tax_today > 0 else 0, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                            #rec.debit = amount_currency
                        else:
                            if rec.move_id.currency_id == self.env.company.currency_id_dif:
                                debit_usd = float_round((rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1)), precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                                rec.write({'debit_usd': debit_usd})
                            else:
                                #busca la tasa de la moneda
                                #rate = self.env['res.currency.rate'].search(
                                #    [('currency_id', '=', rec.move_id.currency_id.id), ('name', '=', rec.move_id.date), ('company_id', '=', rec.company_id.id)])
                                rate = self.env['res.currency']._get_conversion_rate(
                                    from_currency=rec.move_id.currency_id,
                                    to_currency=self.env.company.currency_id_dif,
                                    company=rec.company_id,
                                    date=rec.move_id.date,
                                )
                                if rate:
                                    rec.debit_usd = float_round((rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1)) * rate, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))

            else:
                rec.debit_usd = 0

    @api.depends('amount_currency', 'tax_today','credit','move_id.currency_id')
    def _credit_usd(self):
        for rec in self:
            # tmp = rec.credit_usd if rec.credit_usd > 0 else 0
            if not rec.credit == 0 and rec.display_type not in ['line_section', 'line_note']:
                if not rec.no_calcular:
                    if rec.display_type == 'cogs':
                        #calcular el costo de venta en $
                        rec.credit_usd = float_round(rec.product_id.standard_price_usd * rec.quantity, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                    else:
                        if rec.move_id.currency_id == rec.company_id.currency_id:
                            if rec.display_type == 'product' and rec.move_id.move_type in ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']:
                                rec.credit_usd = float_round(rec.price_subtotal_usd, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                            else:
                                amount_currency = (rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1))
                                rec.credit_usd = float_round((amount_currency / rec.tax_today) if rec.tax_today > 0 else 0, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                                #rec.credit = amount_currency
                        else:
                            if rec.move_id.currency_id == self.env.company.currency_id_dif:
                                rec.credit_usd = float_round(rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1), precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))
                            else:
                                #busca la tasa de la moneda
                                rate = self.env['res.currency']._get_conversion_rate(
                                    from_currency=rec.move_id.currency_id,
                                    to_currency=self.env.company.currency_id_dif,
                                    company=rec.company_id,
                                    date=rec.move_id.date,
                                )
                                if rate:
                                    rec.credit_usd = float_round((rec.amount_currency if rec.amount_currency > 0 else (rec.amount_currency * -1)) * rate, precision_rounding=10**(-rec.company_id.currency_id_dif.decimal_places))


            else:
                rec.credit_usd = 0

    @api.depends('debit','credit','debit_usd', 'credit_usd', 'amount_currency', 'account_id', 'currency_id', 'move_id.state',
                 'company_id','matched_debit_ids', 'matched_credit_ids','amount_residual')
    def _compute_amount_residual_usd(self):
        """ Computes the residual amount of a move line from a reconcilable account in the company currency and the line's currency.
            This amount will be 0 for fully reconciled lines or lines from a non-reconcilable account, the original line amount
            for unreconciled lines, and something in-between for partially reconciled lines.
        """
        for line in self:
            if line.id and (line.account_id.reconcile):
                reconciled_balance = sum(line.matched_credit_ids.mapped('amount_usd')) \
                                     - sum(line.matched_debit_ids.mapped('amount_usd'))

                line.amount_residual_usd = (line.debit_usd - line.credit_usd) - reconciled_balance

                line.reconciled = (line.amount_residual_usd == 0) and not line.amount_residual
            else:
                # Must not have any reconciliation since the line is not eligible for that.
                line.amount_residual_usd = 0.0
                line.reconciled = False


    #nuevo método para reconciliar en v17
    @api.model
    def _reconcile_plan(self, reconciliation_plan):
        """ Reconcile the amls following the reconciliation plan.
        The plan passed as parameter is a list of either a recordset of amls, either another plan.

        For example:
        [account.move.line(1, 2), account.move.line(3, 4)] means:
        - account.move.line(1, 2) will be reconciled first.
        - account.move.line(3, 4) will be reconciled after.

        [[account.move.line(1, 2), account.move.line(3, 4)]] means:
        - account.move.line(1, 2) will be reconciled first.
        - account.move.line(3, 4) will be reconciled after.
        - account.move.line(1, 2, 3, 4).filtered(lambda x: not x.reconciled) will be reconciled at the end.

        :param reconciliation_plan: A list of reconciliation to perform.
        """
        # Parameter allowing to disable the exchange journal entries on partials.
        disable_partial_exchange_diff = bool(
            self.env['ir.config_parameter'].sudo().get_param('account.disable_partial_exchange_diff'))
        #####print('si llega a la función')
        # ==== Prepare the reconciliation ====
        # Batch the amls all together to know what should be reconciled and when.
        plan_list, all_amls = self._optimize_reconciliation_plan(reconciliation_plan)
        all_amls._compute_amount_residual_usd()
        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # All of those fields will be cached by the orm. Since the amls are split into multiple batches, the orm is not
        # able to prefetch the data for all of them at once. For that reason, we force the orm to populate the cache
        # before doing anything.
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Track the invoice's state to call the hook when they become paid ====
        pre_hook_data = all_amls._reconcile_pre_hook()

        # ==== Collect amls data ====
        # All residual amounts are collected and updated until the creation of partials in batch.
        # This is done that way to minimize the orm time for fields invalidation/mark as recompute and
        # recomputation.
        aml_values_map = {
            aml: {
                'aml': aml,
                'amount_residual': aml.amount_residual,
                'amount_residual_usd': aml.amount_residual_usd,
                'amount_residual_currency': aml.amount_residual_currency,
            }
            for aml in all_amls
        }
        ####print('aml_values_map',aml_values_map)
        # ==== Prepare the partials ====
        partials_values_list = []
        exchange_diff_values_list = []
        exchange_diff_partial_index = []
        all_plan_results = []
        partial_index = 0
        for plan in plan_list:
            plan_results = self \
                .with_context(
                no_exchange_difference=self._context.get('no_exchange_difference') or disable_partial_exchange_diff) \
                ._prepare_reconciliation_plan(plan, aml_values_map)
            ####print('plan_results',plan_results)

            all_plan_results.append(plan_results)
            for results in plan_results:
                #actualizar amount en partial_values agregar el menor de los dos valores
                partials_values_list.append(results['partial_values'])
                # if results.get('exchange_values') and results['exchange_values']['move_values']['line_ids']:
                #     exchange_diff_values_list.append(results['exchange_values'])
                #     exchange_diff_partial_index.append(partial_index)
                #     partial_index += 1

        # ==== Create the partials ====
        # Link the newly created partials to the plan. There are needed later for caba exchange entries.
        partials = self.env['account.partial.reconcile'].create(partials_values_list)
        for parcial in partials:
            amount_usd = min(abs(parcial.debit_move_id.amount_residual_usd),
                                 abs(parcial.credit_move_id.amount_residual_usd))
            parcial.write({'amount_usd': abs(amount_usd)})
        start_range = 0
        for plan_results, plan in zip(all_plan_results, plan_list):
            size = len(plan_results)
            plan['partials'] = partials[start_range:start_range + size]
            start_range += size

        # ==== Create the partial exchange journal entries ====
        exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        for index, exchange_move in zip(exchange_diff_partial_index, exchange_moves):
            partials[index].exchange_move_id = exchange_move

        # ==== Create entries for cash basis taxes ====
        def is_cash_basis_needed(account):
            return account.company_id.tax_exigibility \
                and account.account_type in ('asset_receivable', 'liability_payable')

        if not self._context.get('move_reverse_cancel') and not self._context.get('no_cash_basis'):
            for plan in plan_list:
                if is_cash_basis_needed(plan['amls'].account_id):
                    plan['partials']._create_tax_cash_basis_moves()

        # ==== Prepare full reconcile creation ====
        # First, we need to find all sub-set of amls that are candidates for a full.

        def is_line_reconciled(aml, has_multiple_currencies):
            # Check if the journal item passed as parameter is now fully reconciled.
            if aml.reconciled:
                return True
            if not aml.matched_debit_ids and not aml.matched_credit_ids:
                # Suppose a journal item having balance = 0 but an amount_currency like an exchange difference.
                return False
            if has_multiple_currencies:
                return aml.company_currency_id.is_zero(aml.amount_residual)
            else:
                return aml.currency_id.is_zero(aml.amount_residual_currency)

        full_batches = []
        all_aml_ids = set()
        for plan in plan_list:
            for aml in plan['amls']:
                if 'full_batch_index' in aml_values_map[aml]:
                    continue

                involved_amls = plan['amls']._all_reconciled_lines()
                all_aml_ids.update(involved_amls.ids)
                full_batch_index = len(full_batches)
                has_multiple_currencies = len(involved_amls.currency_id) > 1
                is_fully_reconciled = all(
                    is_line_reconciled(involved_aml, has_multiple_currencies)
                    for involved_aml in involved_amls
                )
                full_batches.append({
                    'amls': involved_amls,
                    'is_fully_reconciled': is_fully_reconciled,
                })
                for involved_aml in involved_amls:
                    if aml_values_map.get(involved_aml):
                        aml_values_map[involved_aml]['full_batch_index'] = full_batch_index

        # ==== Prefetch the fields all at once to speedup the reconciliation ====
        # Again, we do the same optimization for the prefetching. We need to do it again since most of the values have
        # been invalidated with the creation of the account.partial.reconcile records.
        all_amls = self.browse(list(all_aml_ids))
        all_amls.move_id
        all_amls.matched_debit_ids
        all_amls.matched_credit_ids

        # ==== Prepare the full exchange journal entries ====
        # This part could be bypassed using the 'no_exchange_difference' key inside the context. This is useful
        # when importing a full accounting including the reconciliation like Winbooks.

        exchange_diff_values_list = []
        exchange_diff_full_batch_index = []
        if not self._context.get('no_exchange_difference'):
            for fulL_batch_index, full_batch in enumerate(full_batches):
                involved_amls = full_batch['amls']
                if not full_batch['is_fully_reconciled']:
                    continue

                # In normal cases, the exchange differences are already generated by the partial at this point meaning
                # there is no journal item left with a zero amount residual in one currency but not in the other.
                # However, after a migration coming from an older version with an older partial reconciliation or due to
                # some rounding issues (when dealing with different decimal places for example), we could need an extra
                # exchange difference journal entry to handle them.
                exchange_lines_to_fix = self.env['account.move.line']
                amounts_list = []
                exchange_max_date = date.min
                for aml in involved_amls:
                    if not aml.company_currency_id.is_zero(aml.amount_residual):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual': aml.amount_residual})
                    elif not aml.currency_id.is_zero(aml.amount_residual_currency):
                        exchange_lines_to_fix += aml
                        amounts_list.append({'amount_residual_currency': aml.amount_residual_currency})
                    exchange_max_date = max(exchange_max_date, aml.date)
                exchange_diff_values = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    company=involved_amls.company_id,
                    exchange_date=exchange_max_date,
                )

                # Exchange difference for cash basis entries.
                # If we are fully reversing the entry, no need to fix anything since the journal entry
                # is exactly the mirror of the source journal entry.
                caba_lines_to_reconcile = None
                if is_cash_basis_needed(involved_amls.account_id) and not self._context.get('move_reverse_cancel'):
                    caba_lines_to_reconcile = involved_amls._add_exchange_difference_cash_basis_vals(
                        exchange_diff_values)

                # Prepare the exchange difference.
                if exchange_diff_values['move_values']['line_ids']:
                    exchange_diff_full_batch_index.append(fulL_batch_index)
                    exchange_diff_values_list.append(exchange_diff_values)
                    full_batch['caba_lines_to_reconcile'] = caba_lines_to_reconcile

        # ==== Create the full exchange journal entries ====
        #exchange_moves = self._create_exchange_difference_moves(exchange_diff_values_list)
        # for fulL_batch_index, exchange_move in zip(exchange_diff_full_batch_index, exchange_moves):
        #     full_batch = full_batches[full_batch_index]
        #     amls = full_batch['amls']
        #     full_batch['exchange_move'] = exchange_move
        #     exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == amls.account_id)
        #     full_batch['amls'] |= exchange_move_lines

        #####print('pasa hasta exchange_moves')
        # ==== Create the full reconcile ====
        # Note we are using Command.link and not Command.set because Command.set is triggering an unlink that is
        # slowing down the assignation of the co-fields. Indeed, unlink is forcing a flush.
        full_reconcile_values_list = []
        full_reconcile_fulL_batch_index = []
        for fulL_batch_index, full_batch in enumerate(full_batches):
            amls = full_batch['amls']
            involved_partials = amls.matched_debit_ids + amls.matched_credit_ids
            if full_batch['is_fully_reconciled']:
                full_reconcile_values_list.append({
                    'exchange_move_id': full_batch.get('exchange_move') and full_batch['exchange_move'].id,
                    'partial_reconcile_ids': [Command.link(partial.id) for partial in involved_partials],
                    'reconciled_line_ids': [Command.link(aml.id) for aml in amls],
                })
                full_reconcile_fulL_batch_index.append(fulL_batch_index)

        self.env['account.full.reconcile'] \
            .with_context(
            skip_invoice_sync=True,
            skip_invoice_line_sync=True,
            skip_account_move_synchronization=True,
            check_move_validity=False,
        ) \
            .create(full_reconcile_values_list)
        #####print('pasa hasta account.full.reconcile')
        # === Cash basis rounding autoreconciliation ===
        # In case a cash basis rounding difference line got created for the transition account, we reconcile it with the corresponding lines
        # on the cash basis moves (so that it reaches full reconciliation and creates an exchange difference entry for this account as well)
        for fulL_batch_index, full_batch in enumerate(full_batches):
            if not full_batch.get('caba_lines_to_reconcile'):
                continue

            caba_lines_to_reconcile = full_batch['caba_lines_to_reconcile']
            exchange_move = full_batch['exchange_move']
            for (dummy, account, repartition_line), amls_to_reconcile in caba_lines_to_reconcile.items():
                if not account.reconcile:
                    continue

                exchange_line = exchange_move.line_ids.filtered(
                    lambda l: l.account_id == account and l.tax_repartition_line_id == repartition_line
                )

                (exchange_line + amls_to_reconcile) \
                    .filtered(lambda l: not l.reconciled) \
                    .reconcile()


        #agarra todos los parciales, busca si debit es factura y credit es pago, o viceversa
        for partial in partials:
            company_id = partial.debit_move_id.move_id.company_id if not partial.debit_move_id.move_id.company_id.parent_id else partial.debit_move_id.move_id.company_id.parent_id
            if company_id.automatic_diff_entry:
                if partial.debit_move_id.move_id.move_type in ['out_invoice'] and partial.credit_move_id.move_id.payment_id:
                    if not partial.credit_move_id.move_id.payment_id.mantener_bs:
                        #factura de cliente y pago
                        tasa_factura = partial.debit_move_id.move_id.tax_today
                        tasa_pago = partial.credit_move_id.move_id.tax_today
                        if tasa_pago>tasa_factura:
                            #crear un asiento de ajuste por diferencial solo en Bs con tasa 0 y cruzar con el pago
                            monto = partial.amount_usd * (tasa_pago - tasa_factura)
                            monto = float_round(monto, precision_rounding=10**(-company_id.currency_id.decimal_places))  #redondear
                            if((abs(partial.credit_move_id.amount_residual) - monto) < 1):
                                monto = abs(partial.credit_move_id.amount_residual)
                            move_data = {
                                'journal_id': company_id.currency_exchange_journal_id.id,
                                'date': partial.credit_move_id.move_id.date,
                                'ref': 'Diferencial de tasa de cambio',
                                'company_id': company_id.id,
                                'currency_id': company_id.currency_id.id,
                                'tax_today': 0,
                                'move_type': 'entry',
                                'line_ids': [(0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': partial.credit_move_id.account_id.id,
                                    'partner_id': partial.credit_move_id.partner_id.id,
                                    'debit': monto,
                                    'credit': 0,
                                    'amount_currency': monto,
                                }), (0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': company_id.income_currency_exchange_account_id.id,
                                    'debit': 0,
                                    'credit': monto,
                                    'amount_currency': -monto,
                                })]
                            }
                            move = self.env['account.move'].create(move_data)
                            move._post(True)
                            #conciliar el asiento con el pago
                            line_new = move.line_ids.filtered(lambda x: x.account_id == partial.credit_move_id.account_id)
                            #flush()
                            self.env.cr.flush()
                            (line_new + partial.credit_move_id).reconcile()
                            parcial.credit_move_id.move_id.payment_id.write({'diferencial_move_ids': [(4, move.id)]})
                            parcial.diferencial_id = move
                        elif tasa_pago<tasa_factura:
                            #crear un asiento de ajuste por diferencial solo en Bs con tasa 0 por perdida y cruzar con la factura
                            monto = partial.amount_usd * (tasa_factura - tasa_pago)
                            monto = float_round(monto, precision_rounding=10**(-company_id.currency_id.decimal_places))
                            if((abs(partial.debit_move_id.amount_residual) - monto) < 1):
                                monto = abs(partial.debit_move_id.amount_residual)
                            move_data = {
                                'journal_id': company_id.currency_exchange_journal_id.id,
                                'date': partial.debit_move_id.move_id.date,
                                'ref': 'Diferencial de tasa de cambio',
                                'company_id': company_id.id,
                                'currency_id': company_id.currency_id.id,
                                'tax_today': 0,
                                'line_ids': [(0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': partial.debit_move_id.account_id.id,
                                    'partner_id': partial.debit_move_id.partner_id.id,
                                    'debit': 0,
                                    'credit': monto,
                                    'no_calcular': True,
                                    'amount_currency': -monto,
                                }), (0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': company_id.expense_currency_exchange_account_id.id,
                                    'debit': monto,
                                    'credit': 0,
                                    'no_calcular': True,
                                    'amount_currency': monto,
                                })]
                            }
                            move = self.env['account.move'].create(move_data)
                            move._post(True)
                            #conciliar el asiento con la factura
                            line_new = move.line_ids.filtered(lambda x: x.account_id == partial.debit_move_id.account_id)
                            (line_new + partial.debit_move_id).reconcile()
                            parcial.credit_move_id.move_id.payment_id.write({'diferencial_move_ids': [(4, move.id)]})
                            parcial.diferencial_id = move
                elif partial.credit_move_id.move_id.move_type in ['in_invoice'] and partial.debit_move_id.move_id.payment_id:
                    if not partial.debit_move_id.move_id.payment_id.mantener_bs:
                        #factura de proveedor y pago
                        tasa_factura = partial.credit_move_id.move_id.tax_today
                        tasa_pago = partial.debit_move_id.move_id.tax_today
                        if tasa_pago>tasa_factura:
                            #crear un asiento de ajuste por diferencial solo en Bs con tasa 0 y cruzar con el pago
                            monto = partial.amount_usd * (tasa_pago - tasa_factura)
                            monto = float_round(monto, precision_rounding=10**(-company_id.currency_id.decimal_places))
                            if((abs(partial.debit_move_id.amount_residual) - monto) < 1):
                                monto = abs(partial.debit_move_id.amount_residual)
                            move_data = {
                                'journal_id': company_id.currency_exchange_journal_id.id,
                                'date': partial.debit_move_id.move_id.date,
                                'ref': 'Diferencial de tasa de cambio',
                                'company_id': company_id.id,
                                'currency_id': company_id.currency_id.id,
                                'tax_today': 0,
                                'move_type': 'entry',
                                'line_ids': [(0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': partial.debit_move_id.account_id.id,
                                    'partner_id': partial.debit_move_id.partner_id.id,
                                    'debit': 0,
                                    'credit': monto,
                                    'amount_currency': -monto,
                                }), (0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': company_id.expense_currency_exchange_account_id.id,
                                    'debit': monto,
                                    'credit': 0,
                                    'amount_currency': monto,
                                })]
                            }
                            move = self.env['account.move'].create(move_data)
                            move._post(True)
                            #conciliar el asiento con el pago
                            line_new = move.line_ids.filtered(lambda x: x.account_id == partial.debit_move_id.account_id)
                            (line_new + partial.debit_move_id).reconcile()
                            #agregar el asiento diferencial_move_ids de pagos
                            parcial.debit_move_id.move_id.payment_id.write({'diferencial_move_ids': [(4, move.id)]})
                            parcial.diferencial_id = move
                        elif tasa_pago<tasa_factura:
                            #crear un asiento de ajuste por diferencial solo en Bs con tasa 0 por ganancia y cruzar con la factura
                            monto = partial.amount_usd * (tasa_factura - tasa_pago)
                            monto = float_round(monto, precision_rounding=10**(-company_id.currency_id.decimal_places))
                            if((abs(partial.credit_move_id.amount_residual) - monto) < 1):
                                monto = abs(partial.credit_move_id.amount_residual)
                            move_data = {
                                'journal_id': company_id.currency_exchange_journal_id.id,
                                'date': partial.credit_move_id.move_id.date,
                                'ref': 'Diferencial de tasa de cambio',
                                'company_id': company_id.id,
                                'currency_id': company_id.currency_id.id,
                                'tax_today': 0,
                                'move_type': 'entry',
                                'line_ids': [(0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': partial.credit_move_id.account_id.id,
                                    'partner_id': partial.credit_move_id.partner_id.id,
                                    'debit': monto,
                                    'credit': 0,
                                    'amount_currency': monto,
                                }), (0, 0, {
                                    'name': 'Diferencial de tasa de cambio',
                                    'account_id': company_id.income_currency_exchange_account_id.id,
                                    'debit': 0,
                                    'credit': monto,
                                    'amount_currency': -monto,
                                })]
                            }
                            move = self.env['account.move'].create(move_data)
                            move._post(True)
                            #conciliar el asiento con la factura
                            line_new = move.line_ids.filtered(lambda x: x.account_id == partial.credit_move_id.account_id)
                            (line_new + partial.credit_move_id).reconcile()
                            parcial.debit_move_id.move_id.payment_id.write({'diferencial_move_ids': [(4, move.id)]})
                            parcial.diferencial_id = move
        all_amls._compute_amount_residual_usd()
        all_amls._reconcile_post_hook(pre_hook_data)

    def _apply_price_difference(self):
        svl_vals_list = []
        aml_vals_list = []
        if self.env.company.anglo_saxon_accounting:
            for line in self:
                #se coloca continue para no hacer diferencia en anglosajona
                #continue
                line = line.with_company(line.company_id)
                po_line = line.purchase_line_id
                uom = line.product_uom_id or line.product_id.uom_id

                # Don't create value for more quantity than received
                quantity = po_line.qty_received - (po_line.qty_invoiced - line.quantity)
                quantity = max(min(line.quantity, quantity), 0)
                if float_is_zero(quantity, precision_rounding=uom.rounding):
                    continue

                layers = line._get_valued_in_moves().stock_valuation_layer_ids.filtered(
                    lambda svl: svl.product_id == line.product_id and not svl.stock_valuation_layer_id)
                if not layers:
                    continue
                #####print('pasa hasta layers',layers)
                new_svl_vals_list, new_aml_vals_list = line._generate_price_difference_vals(layers)
                svl_vals_list += new_svl_vals_list
                aml_vals_list += new_aml_vals_list
                #####print('pasa hasta _apply_price_difference', svl_vals_list, aml_vals_list)
                #raise
        return self.env['stock.valuation.layer'].sudo().create(svl_vals_list), self.env['account.move.line'].sudo().create(aml_vals_list)

    def _prepare_analytic_distribution_line(self, distribution, account_ids, distribution_on_each_plan):
        """ Prepare the values used to create() an account.analytic.line upon validation of an account.move.line having
            analytic tags with analytic distribution.
        """
        self.ensure_one()
        account_field_values = {}
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        amount = 0
        amount_usd = 0
        for account in self.env['account.analytic.account'].browse(map(int, account_ids.split(","))).exists():
            distribution_plan = distribution_on_each_plan.get(account.root_plan_id, 0) + distribution
            if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
                amount = -self.balance * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
                amount_usd = -self.balance_usd * (100 - distribution_on_each_plan.get(account.root_plan_id, 0)) / 100.0
            else:
                amount = -self.balance * distribution / 100.0
                amount_usd = -self.balance_usd * distribution / 100.0
            distribution_on_each_plan[account.root_plan_id] = distribution_plan
            account_field_values[account.plan_id._column_name()] = account.id
        default_name = self.name or (self.ref or '/' + ' -- ' + (self.partner_id and self.partner_id.name or '/'))
        return {
            'name': default_name,
            'date': self.date,
            **account_field_values,
            'partner_id': self.partner_id.id,
            'unit_amount': self.quantity,
            'product_id': self.product_id and self.product_id.id or False,
            'product_uom_id': self.product_uom_id and self.product_uom_id.id or False,
            'amount': amount,
            'amount_usd': amount_usd,
            'general_account_id': self.account_id.id,
            'ref': self.ref,
            'move_line_id': self.id,
            'user_id': self.move_id.invoice_user_id.id or self._uid,
            'company_id': self.company_id.id or self.env.company.id,
            'category': 'invoice' if self.move_id.is_sale_document() else 'vendor_bill' if self.move_id.is_purchase_document() else 'other',
        }

    @api.model
    def _prepare_reconciliation_single_partial(self, debit_values, credit_values, shadowed_aml_values=None):
        """ Prepare the values to create an account.partial.reconcile later when reconciling the dictionaries passed
        as parameters, each one representing an account.move.line.
        :param debit_values:  The values of account.move.line to consider for a debit line.
        :param credit_values: The values of account.move.line to consider for a credit line.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: A dictionary:
            * debit_values:     None if the line has nothing left to reconcile.
            * credit_values:    None if the line has nothing left to reconcile.
            * partial_values:   The newly computed values for the partial.
            * exchange_values:  The values to create an exchange difference linked to this partial.
        """
        # ==== Determine the currency in which the reconciliation will be done ====
        # In this part, we retrieve the residual amounts, check if they are zero or not and determine in which
        # currency and at which rate the reconciliation will be done.
        res = {
            'debit_values': debit_values,
            'credit_values': credit_values,
        }
        debit_aml = debit_values['aml']
        credit_aml = credit_values['aml']
        debit_currency = debit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        credit_currency = credit_aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        company_currency = debit_aml.company_currency_id

        remaining_debit_amount_curr = debit_values['amount_residual_currency']
        remaining_credit_amount_curr = credit_values['amount_residual_currency']
        remaining_debit_amount = debit_values['amount_residual']
        remaining_credit_amount = credit_values['amount_residual']

        #verificar si debit_aml es una factura
        if debit_aml.move_id.move_type not in ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']:
            if debit_aml.currency_id == debit_aml.company_id.currency_id:
                extra_context_debit = {'forced_rate_from_register_payment': (1 / debit_aml.tax_today) if debit_aml.tax_today > 0 else 1}

                debit_available_residual_amounts = self.with_context(**extra_context_debit)._prepare_move_line_residual_amounts(
                    debit_values,
                    credit_currency,
                    shadowed_aml_values=shadowed_aml_values,
                    other_aml_values=credit_values,
                )
                ###print('debit_available_residual_amounts',debit_available_residual_amounts)
            else:
                debit_available_residual_amounts = self._prepare_move_line_residual_amounts(
                    debit_values,
                    credit_currency,
                    shadowed_aml_values=shadowed_aml_values,
                    other_aml_values=credit_values,
                )
        else:
            debit_available_residual_amounts = self._prepare_move_line_residual_amounts(
                debit_values,
                credit_currency,
                shadowed_aml_values=shadowed_aml_values,
                other_aml_values=credit_values,
            )

        if credit_aml.move_id.move_type not in ['in_invoice', 'in_refund', 'out_invoice', 'out_refund']:
            if credit_aml.currency_id == credit_aml.company_id.currency_id:
                extra_context_credit = {'forced_rate_from_register_payment': (1 / credit_aml.tax_today) if credit_aml.tax_today > 0 else 1}
                credit_available_residual_amounts = self.with_context(**extra_context_credit)._prepare_move_line_residual_amounts(
                    credit_values,
                    debit_currency,
                    shadowed_aml_values=shadowed_aml_values,
                    other_aml_values=debit_values,
                )
                ###print('credit_available_residual_amounts',credit_available_residual_amounts)
            else:
                credit_available_residual_amounts = self._prepare_move_line_residual_amounts(
                    credit_values,
                    debit_currency,
                    shadowed_aml_values=shadowed_aml_values,
                    other_aml_values=debit_values,
                )
        else:
            credit_available_residual_amounts = self._prepare_move_line_residual_amounts(
                credit_values,
                debit_currency,
                shadowed_aml_values=shadowed_aml_values,
                other_aml_values=debit_values,
            )

        if debit_currency != company_currency \
                and debit_currency in debit_available_residual_amounts \
                and debit_currency in credit_available_residual_amounts:
            recon_currency = debit_currency
        elif credit_currency != company_currency \
                and credit_currency in debit_available_residual_amounts \
                and credit_currency in credit_available_residual_amounts:
            recon_currency = credit_currency
        else:
            recon_currency = company_currency

        debit_recon_values = debit_available_residual_amounts.get(recon_currency)
        credit_recon_values = credit_available_residual_amounts.get(recon_currency)

        # Check if there is something left to reconcile. Move to the next loop iteration if not.
        skip_reconciliation = False
        if not debit_recon_values:
            res['debit_values'] = None
            skip_reconciliation = True
        if not credit_recon_values:
            res['credit_values'] = None
            skip_reconciliation = True
        if skip_reconciliation:
            return res

        recon_debit_amount = debit_recon_values['residual']
        recon_credit_amount = -credit_recon_values['residual']

        # ==== Match both lines together and compute amounts to reconcile ====

        # Special case for exchange difference lines. In that case, both lines are sharing the same foreign
        # currency but at least one has no amount in foreign currency.
        # In that case, we don't want a rate for the opposite line because the exchange difference is supposed
        # to reduce only the amount in company currency but not the foreign one.
        exchange_line_mode = \
            recon_currency == company_currency \
            and debit_currency == credit_currency \
            and (
                    not debit_available_residual_amounts.get(debit_currency)
                    or not credit_available_residual_amounts.get(credit_currency)
            )

        # Determine which line is fully matched by the other.
        compare_amounts = recon_currency.compare_amounts(recon_debit_amount, recon_credit_amount)
        min_recon_amount = min(recon_debit_amount, recon_credit_amount)
        debit_fully_matched = compare_amounts <= 0
        credit_fully_matched = compare_amounts >= 0

        # ==== Computation of partial amounts ====
        if recon_currency == company_currency:
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_available_residual_amounts.get(debit_currency, {}).get('rate')
                credit_rate = credit_available_residual_amounts.get(credit_currency, {}).get('rate')

            # Compute the partial amount expressed in company currency.
            partial_amount = min_recon_amount

            if debit_aml.move_id.move_type in ['out_invoice'] and credit_aml.move_id.payment_id:
                # debito es factura de cliente y credito es pago
                tasa_factura = debit_aml.move_id.tax_today
                tasa_pago = credit_aml.move_id.tax_today

                if not credit_aml.move_id.payment_id.mantener_bs:
                    if tasa_factura < tasa_pago:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_factura) > abs(debit_recon_values['residual'])):
                            partial_amount = abs(debit_recon_values['residual'])
                        else:
                            partial_amount = (residual_usd * tasa_factura)

                    else:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_pago) > abs(debit_recon_values['residual'])):
                            partial_amount = abs(debit_recon_values['residual'])
                        else:
                            partial_amount = (residual_usd * tasa_pago)


            if debit_aml.move_id.payment_id and credit_aml.move_id.move_type in ['in_invoice']:
                # debito es pago y credito es factura de proveedor
                tasa_factura = credit_aml.move_id.tax_today
                tasa_pago = debit_aml.move_id.tax_today
                if not debit_aml.move_id.payment_id.mantener_bs:
                    if tasa_factura < tasa_pago:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_factura) > abs(credit_recon_values['residual'])):
                            partial_amount = abs(credit_recon_values['residual'])
                        else:
                            partial_amount = (residual_usd * tasa_factura)
                    else:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_pago) > abs(credit_recon_values['residual'])):
                            partial_amount = abs(credit_recon_values['residual'])
                        else:
                            partial_amount = (residual_usd * tasa_pago)


            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount_currency = debit_currency.round(debit_rate * partial_amount)
                partial_debit_amount_currency = min(partial_debit_amount_currency, remaining_debit_amount_curr)
            else:
                partial_debit_amount_currency = 0.0
            if credit_rate:
                partial_credit_amount_currency = credit_currency.round(credit_rate * partial_amount)
                partial_credit_amount_currency = min(partial_credit_amount_currency, -remaining_credit_amount_curr)
            else:
                partial_credit_amount_currency = 0.0

        else:
            # recon_currency != company_currency
            if exchange_line_mode:
                debit_rate = None
                credit_rate = None
            else:
                debit_rate = debit_recon_values['rate']
                credit_rate = credit_recon_values['rate']

            # Compute the partial amount expressed in foreign currency.
            if debit_rate:
                partial_debit_amount = company_currency.round(min_recon_amount / debit_rate)
                partial_debit_amount = min(partial_debit_amount, remaining_debit_amount)
            else:
                partial_debit_amount = 0.0
            if credit_rate:
                partial_credit_amount = company_currency.round(min_recon_amount / credit_rate)
                partial_credit_amount = min(partial_credit_amount, -remaining_credit_amount)
            else:
                partial_credit_amount = 0.0
            ##print('partial_debit_amount',partial_debit_amount)
            ##print('partial_credit_amount',partial_credit_amount)

            partial_amount = min(partial_debit_amount, partial_credit_amount)

            if debit_aml.move_id.move_type in ['out_invoice'] and credit_aml.move_id.payment_id:
                # debito es factura de cliente y credito es pago
                tasa_factura = debit_aml.move_id.tax_today
                tasa_pago = credit_aml.move_id.tax_today
                if not credit_aml.move_id.payment_id.mantener_bs:
                    if tasa_factura < tasa_pago:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        ##print('residual_usd', residual_usd)
                        ##print('(residual_usd * tasa_factura)', (residual_usd * tasa_factura))
                        ##print('debit_recon_values',debit_recon_values)
                        ##print('abs(debit_recon_values[residual])', abs(debit_recon_values['residual']))
                        if(float_round((residual_usd * tasa_factura), precision_rounding=10**(-debit_aml.currency_id.decimal_places)) > abs(partial_debit_amount)):
                            partial_amount = abs(partial_debit_amount)
                        else:
                            partial_amount = float_round((residual_usd * tasa_factura), precision_rounding=10**(-debit_aml.currency_id.decimal_places))
                            if abs(partial_amount - partial_debit_amount) <= 0.5:
                                partial_amount = abs(partial_debit_amount)
                        ##print('partial_amount', partial_amount)
                    else:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if(float_round((residual_usd * tasa_pago), precision_rounding=10**(-debit_aml.currency_id.decimal_places)) > abs(partial_debit_amount)):
                            partial_amount = abs(partial_debit_amount)
                        else:
                            partial_amount = float_round((residual_usd * tasa_pago), precision_rounding=10**(-debit_aml.currency_id.decimal_places))
                            if abs(partial_amount - partial_debit_amount) <= 0.5:
                                partial_amount = abs(partial_debit_amount)

            if debit_aml.move_id.payment_id and credit_aml.move_id.move_type in ['in_invoice']:
                # debito es pago y credito es factura de proveedor
                tasa_factura = credit_aml.move_id.tax_today
                tasa_pago = debit_aml.move_id.tax_today
                if not debit_aml.move_id.payment_id.mantener_bs:
                    if tasa_factura < tasa_pago:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_factura) > abs(partial_amount)):
                            pass
                        else:
                            partial_amount = (-residual_usd * tasa_factura)
                    else:
                        residual_usd = min(abs(debit_recon_values['residual_usd']),
                                           abs(credit_recon_values['residual_usd']))
                        if((residual_usd * tasa_pago) > abs(partial_amount)):
                            pass
                        else:
                            partial_amount = (-residual_usd * tasa_pago)

            # Compute the partial amount expressed in foreign currency.
            # Take care to handle the case when a line expressed in company currency is mimicking the foreign
            # currency of the opposite line.
            if debit_currency == company_currency:
                partial_debit_amount_currency = partial_amount
            else:
                partial_debit_amount_currency = min_recon_amount
            if credit_currency == company_currency:
                partial_credit_amount_currency = partial_amount
            else:
                partial_credit_amount_currency = min_recon_amount

            if debit_aml.move_id.move_type in ['out_invoice'] and credit_aml.move_id.tax_today == 0:
                #es una factura en $ con el asiento dediferencial solo en Bs
                partial_debit_amount_currency = 0

            if credit_aml.move_id.move_type in ['in_invoice'] and debit_aml.move_id.tax_today == 0:
                #es una factura en $ con el asiento dediferencial solo en Bs
                partial_credit_amount_currency = 0



        # Computation of the partial exchange difference. You can skip this part using the
        # `no_exchange_difference` context key (when reconciling an exchange difference for example).
        #if not self._context.get('no_exchange_difference') or False:
        if False:
            exchange_lines_to_fix = self.env['account.move.line']
            amounts_list = []
            if recon_currency == company_currency:
                if debit_fully_matched:
                    debit_exchange_amount = remaining_debit_amount_curr - partial_debit_amount_currency
                    if not debit_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual_currency': debit_exchange_amount})
                        remaining_debit_amount_curr -= debit_exchange_amount
                if credit_fully_matched:
                    credit_exchange_amount = remaining_credit_amount_curr + partial_credit_amount_currency
                    if not credit_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual_currency': credit_exchange_amount})
                        remaining_credit_amount_curr += credit_exchange_amount

            else:
                if debit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    debit_exchange_amount = remaining_debit_amount - partial_amount
                    if not company_currency.is_zero(debit_exchange_amount):
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    debit_exchange_amount = partial_debit_amount - partial_amount
                    if company_currency.compare_amounts(debit_exchange_amount, 0.0) > 0:
                        exchange_lines_to_fix += debit_aml
                        amounts_list.append({'amount_residual': debit_exchange_amount})
                        remaining_debit_amount -= debit_exchange_amount
                        if debit_currency == company_currency:
                            remaining_debit_amount_curr -= debit_exchange_amount

                if credit_fully_matched:
                    # Create an exchange difference on the remaining amount expressed in company's currency.
                    credit_exchange_amount = remaining_credit_amount + partial_amount
                    if not company_currency.is_zero(credit_exchange_amount):
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount
                else:
                    # Create an exchange difference ensuring the rate between the residual amounts expressed in
                    # both foreign and company's currency is still consistent regarding the rate between
                    # 'amount_currency' & 'balance'.
                    credit_exchange_amount = partial_amount - partial_credit_amount
                    if company_currency.compare_amounts(credit_exchange_amount, 0.0) < 0:
                        exchange_lines_to_fix += credit_aml
                        amounts_list.append({'amount_residual': credit_exchange_amount})
                        remaining_credit_amount -= credit_exchange_amount
                        if credit_currency == company_currency:
                            remaining_credit_amount_curr -= credit_exchange_amount

            if exchange_lines_to_fix:
                res['exchange_values'] = exchange_lines_to_fix._prepare_exchange_difference_move_vals(
                    amounts_list,
                    exchange_date=max(
                        debit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                        credit_aml._get_reconciliation_aml_field_value('date', shadowed_aml_values),
                    ),
                )

        # ==== Create partials ====

        remaining_debit_amount -= partial_amount
        remaining_credit_amount += partial_amount
        remaining_debit_amount_curr -= partial_debit_amount_currency
        remaining_credit_amount_curr += partial_credit_amount_currency

        res['partial_values'] = {
            'amount': partial_amount,
            'debit_amount_currency': partial_debit_amount_currency,
            'credit_amount_currency': partial_credit_amount_currency,
            'debit_move_id': debit_aml.id,
            'credit_move_id': credit_aml.id,
        }
        ##print('res[partial_values]',res['partial_values'])
        debit_values['amount_residual'] = remaining_debit_amount
        debit_values['amount_residual_currency'] = remaining_debit_amount_curr
        credit_values['amount_residual'] = remaining_credit_amount
        credit_values['amount_residual_currency'] = remaining_credit_amount_curr

        if debit_fully_matched:
            res['debit_values'] = None
        if credit_fully_matched:
            res['credit_values'] = None
        return res

    def remove_move_reconcile(self):
        #super
        super(AccountMoveLine, self).remove_move_reconcile()
        self._compute_balance_usd()
        self._compute_amount_residual_usd()
        self.reconciled = False

    @api.model
    def _prepare_reconciliation_amls(self, values_list, shadowed_aml_values=None):
        """ Prepare the partials on the current journal items to perform the reconciliation.
        Note: The order of records in self is important because the journal items will be reconciled using this order.

        :param values_list: A list of dictionaries, one for each aml.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :return: a tuple of
            1) list of vals for partial reconciliation creation,
            2) the list of vals for the exchange difference entries to be created
        """
        ####print('si llega a la función-----------',values_list)
        debit_values_list = iter([
            x
            for x in values_list
            if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) > 0.0
               or x['aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) > 0.0
        ])
        credit_values_list = iter([
            x
            for x in values_list
            if x['aml']._get_reconciliation_aml_field_value('balance', shadowed_aml_values) < 0.0
               or x['aml']._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values) < 0.0
        ])
        ####print('debit_values_list',debit_values_list)
        ####print('credit_values_list',credit_values_list)
        debit_values = None
        credit_values = None
        fully_reconciled_aml_ids = set()
        all_results = []

        while True:

            # ==== Find the next available lines ====
            # For performance reasons, the partials are created all at once meaning the residual amounts can't be
            # trusted from one iteration to another. That's the reason why all residual amounts are kept as variables
            # and reduced "manually" every time we append a dictionary to 'partials_values_list'.

            # Move to the next available debit line.
            if not debit_values:
                debit_values = next(debit_values_list, None)
                if not debit_values:
                    break

            # Move to the next available credit line.
            if not credit_values:
                credit_values = next(credit_values_list, None)
                if not credit_values:
                    break

            # ==== Compute the amounts to reconcile ====
            #agregar amount_residual_usd a partir de debit_values[aml].amount_residual_usd
            debit_values['amount_residual_usd'] = debit_values['aml'].amount_residual_usd

            #agregar amount_residual_usd a partir de credit_values[aml].amount_residual_usd
            credit_values['amount_residual_usd'] = credit_values['aml'].amount_residual_usd
            ####print('pasando despues del next',debit_values,credit_values)
            results = self._prepare_reconciliation_single_partial(
                debit_values,
                credit_values,
                shadowed_aml_values=shadowed_aml_values,
            )
            if results.get('partial_values'):
                all_results.append(results)
            if results['debit_values'] is None:
                fully_reconciled_aml_ids.add(debit_values['aml'].id)
                debit_values = None
            if results['credit_values'] is None:
                fully_reconciled_aml_ids.add(credit_values['aml'].id)
                credit_values = None

        return all_results, fully_reconciled_aml_ids

    @api.model
    def _prepare_move_line_residual_amounts(self, aml_values, counterpart_currency, shadowed_aml_values=None,
                                            other_aml_values=None):
        """ Prepare the available residual amounts for each currency.
        :param aml_values: The values of account.move.line to consider.
        :param counterpart_currency: The currency of the opposite line this line will be reconciled with.
        :param shadowed_aml_values: A mapping aml -> dictionary to replace some original aml values to something else.
                                    This is usefull if you want to preview the reconciliation before doing some changes
                                    on amls like changing a date or an account.
        :param other_aml_values:    The other aml values to be reconciled with the current one.
        :return: A mapping currency -> dictionary containing:
            * residual: The residual amount left for this currency.
            * rate:     The rate applied regarding the company's currency.
        """

        def is_payment(aml):
            return aml.move_id.payment_id or aml.move_id.statement_line_id

        def get_odoo_rate(aml, other_aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            if other_aml and not is_payment(aml) and is_payment(other_aml):
                return get_accounting_rate(other_aml, currency)
            if aml.move_id.is_invoice(include_receipts=True):
                exchange_rate_date = aml.move_id.invoice_date
            else:
                exchange_rate_date = aml._get_reconciliation_aml_field_value('date', shadowed_aml_values)
            return currency._get_conversion_rate(aml.company_currency_id, currency, aml.company_id, exchange_rate_date)

        def get_accounting_rate(aml, currency):
            if forced_rate := self._context.get('forced_rate_from_register_payment'):
                return forced_rate
            balance = aml._get_reconciliation_aml_field_value('balance', shadowed_aml_values)
            amount_currency = aml._get_reconciliation_aml_field_value('amount_currency', shadowed_aml_values)
            if not aml.company_currency_id.is_zero(balance) and not currency.is_zero(amount_currency):
                return abs(amount_currency / balance)

        aml = aml_values['aml']

        other_aml = (other_aml_values or {}).get('aml')
        remaining_amount_curr = aml_values['amount_residual_currency']
        remaining_amount = aml_values['amount_residual']
        remaining_amount_usd = aml_values['amount_residual_usd']
        company_currency = aml.company_currency_id
        currency = aml._get_reconciliation_aml_field_value('currency_id', shadowed_aml_values)
        account = aml._get_reconciliation_aml_field_value('account_id', shadowed_aml_values)
        has_zero_residual = company_currency.is_zero(remaining_amount)
        has_zero_residual_currency = currency.is_zero(remaining_amount_curr)
        is_rec_pay_account = account.account_type in ('asset_receivable', 'liability_payable')

        available_residual_per_currency = {}

        if not has_zero_residual:
            available_residual_per_currency[company_currency] = {
                'residual': remaining_amount,
                'residual_usd': remaining_amount_usd,
                'rate': 1,
            }
        if currency != company_currency and not has_zero_residual_currency:
            available_residual_per_currency[currency] = {
                'residual': remaining_amount_curr,
                'residual_usd': remaining_amount_usd,
                'rate': get_accounting_rate(aml, currency),
            }

        if currency == company_currency \
                and is_rec_pay_account \
                and not has_zero_residual \
                and counterpart_currency != company_currency:
            rate = get_odoo_rate(aml, other_aml, counterpart_currency)
            residual_in_foreign_curr = counterpart_currency.round(remaining_amount * rate)
            if not counterpart_currency.is_zero(residual_in_foreign_curr):
                available_residual_per_currency[counterpart_currency] = {
                    'residual': residual_in_foreign_curr,
                    'residual_usd': remaining_amount_usd,
                    'rate': rate,
                }
        elif currency == counterpart_currency \
                and currency != company_currency \
                and not has_zero_residual_currency:
            available_residual_per_currency[counterpart_currency] = {
                'residual': remaining_amount_curr,
                'residual_usd': remaining_amount_usd,
                'rate': get_accounting_rate(aml, currency),
            }

        if not available_residual_per_currency and not remaining_amount_usd == 0:
            available_residual_per_currency[currency] = {
                'residual': 0,
                'residual_usd': remaining_amount_usd,
                'rate': 1,
            }
        ####print('available_residual_per_currency',available_residual_per_currency)
        return available_residual_per_currency





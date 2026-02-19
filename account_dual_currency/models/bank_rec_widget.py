# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models, Command
from odoo.osv import expression
from odoo.tools.misc import formatLang, frozendict

import markupsafe
import uuid

class BankRecWidget(models.Model):
    _inherit = "bank.rec.widget"

    currency_id_dif_statement = fields.Many2one("res.currency",
                                                string="Divisa de Referencia", related='st_line_id.currency_id_dif_statement',depends=['st_line_id'],)

    tasa_referencia_statement = fields.Float(string="Tasa", related='st_line_id.tasa_referencia_statement',depends=['st_line_id'], readonly=False,
                                             digits='Dual_Currency_rate')

    amount_usd_statement = fields.Monetary(currency_field='currency_id_dif_statement', string='Total Ref.',
                                           readonly=False, related='st_line_id.amount_usd_statement',depends=['st_line_id'],
                                           digits='Dual_Currency')

    def _lines_prepare_new_aml_line(self, aml, **kwargs):
        ##print('entra en _lines_prepare_new_aml_line', aml.name)
        if aml.payment_id:
            self.st_line_id.tasa_referencia_statement = aml.payment_id.tax_today
            self.tasa_referencia_statement = aml.payment_id.tax_today
            #self._js_action_reset()
        aml._compute_amount_residual_usd()
        vals = super(BankRecWidget, self)._lines_prepare_new_aml_line(aml, **kwargs)
        vals['currency_id_dif_statement'] = self.currency_id_dif_statement.id
        vals['tasa_referencia_statement'] = self.tasa_referencia_statement
        vals['balance_usd'] = -aml.amount_residual_usd
        #print('vals _lines_prepare_new_aml_line', vals)
        return vals

    def _lines_prepare_auto_balance_line(self):
        vals = super(BankRecWidget, self)._lines_prepare_auto_balance_line()
        balance_usd = vals['balance'] / self.tasa_referencia_statement
        vals['balance_usd'] = round(balance_usd, self.currency_id_dif_statement.decimal_places)
        return vals

    def _js_action_reset(self):
        self.ensure_one()
        st_line = self.st_line_id
        st_line.action_undo_reconciliation()

        # The current record has been invalidated. Reload it completely.
        self.st_line_id = st_line

        self.st_line_id.move_id.line_ids._compute_balance_usd()
        self.st_line_id.move_id.line_ids._compute_amount_residual_usd()
        self._ensure_loaded_lines()
        self._action_trigger_matching_rules()
        self.return_todo_command = {'done': True}

    def _lines_check_apply_partial_matching(self):
        """ Try to apply a partial matching on the currently mounted journal items.
        :return: True if applied, False otherwise.
        """
        all_aml_lines = self.line_ids.filtered(lambda x: x.flag == 'new_aml')
        if all_aml_lines:
            last_line = all_aml_lines[-1]

            # Cleanup the existing partials if not on the last line.
            line_ids_commands = []
            for aml_line in all_aml_lines:
                is_partial = aml_line.display_stroked_amount_currency or aml_line.display_stroked_balance
                if is_partial and not aml_line.manually_modified:
                    line_ids_commands.append(Command.update(aml_line.id, {
                        'amount_currency': aml_line.source_amount_currency,
                        'balance': aml_line.source_balance,
                        'balance_usd': aml_line.source_balance_usd,
                    }))
            if line_ids_commands:
                self.line_ids = line_ids_commands
                self._lines_recompute_exchange_diff()

            # Check for a partial reconciliation.
            partial_amounts = self._lines_check_partial_amount(last_line)
            if partial_amounts:
                # Make a partial: an auto-balance line is no longer necessary.
                last_line.amount_currency = partial_amounts['amount_currency']
                last_line.balance = partial_amounts['balance']
                last_line.balance_usd = partial_amounts['balance_usd']
                exchange_line = partial_amounts['exchange_diff_line']
                if exchange_line:
                    exchange_line.balance = partial_amounts['exchange_balance']
                    if exchange_line.currency_id == self.company_currency_id:
                        exchange_line.amount_currency = exchange_line.balance
                return True

        return False

    def _lines_check_partial_amount(self, line):
        if line.flag != 'new_aml':
            return None

        exchange_diff_line = self.line_ids\
            .filtered(lambda x: x.flag == 'exchange_diff' and x.source_aml_id == line.source_aml_id)
        auto_balance_line_vals = self._lines_prepare_auto_balance_line()
        auto_balance = auto_balance_line_vals['balance']
        auto_balance_usd = auto_balance_line_vals['balance_usd']
        current_balance = line.balance + exchange_diff_line.balance
        current_balance_usd = line.balance_usd
        has_enough_comp_debit = self.company_currency_id.compare_amounts(auto_balance, 0) < 0 < self.company_currency_id.compare_amounts(current_balance, 0) \
                                and self.company_currency_id.compare_amounts(current_balance, -auto_balance) > 0
        has_enough_comp_credit = self.company_currency_id.compare_amounts(auto_balance, 0) > 0 > self.company_currency_id.compare_amounts(current_balance, 0) \
                                 and self.company_currency_id.compare_amounts(-current_balance, auto_balance) > 0

        auto_amount_currency = auto_balance_line_vals['amount_currency']
        current_amount_currency = line.amount_currency
        current_amount_currency_usd = line.balance_usd
        has_enough_curr_debit = line.currency_id.compare_amounts(auto_amount_currency, 0) < 0 < line.currency_id.compare_amounts(current_amount_currency, 0) \
                                and line.currency_id.compare_amounts(current_amount_currency, -auto_amount_currency) > 0
        has_enough_curr_credit = line.currency_id.compare_amounts(auto_amount_currency, 0) > 0 > line.currency_id.compare_amounts(current_amount_currency, 0) \
                                 and line.currency_id.compare_amounts(-current_amount_currency, auto_amount_currency) > 0

        if line.currency_id == self.transaction_currency_id:
            if has_enough_curr_debit or has_enough_curr_credit:
                amount_currency_after_partial = current_amount_currency + auto_amount_currency
                amount_currency_after_partial_usd = current_amount_currency_usd + auto_balance_usd
                # Get the bank transaction rate.
                transaction_amount, _transaction_currency, _journal_amount, _journal_currency, company_amount, _company_currency \
                    = self.st_line_id._get_accounting_amounts_and_currencies()
                rate = abs(company_amount / transaction_amount) if transaction_amount else 0.0

                # Compute the amounts to make a partial.
                balance_after_partial = line.company_currency_id.round(amount_currency_after_partial * rate)
                new_line_balance = line.company_currency_id.round(balance_after_partial * abs(line.balance) / abs(current_balance))
                new_line_balance_usd = abs(line.balance_usd) - abs(amount_currency_after_partial_usd)
                exchange_diff_line_balance = balance_after_partial - new_line_balance
                data = {
                    'exchange_diff_line': exchange_diff_line,
                    'amount_currency': amount_currency_after_partial,
                    'balance': new_line_balance,
                    'balance_usd': new_line_balance_usd,
                    'exchange_balance': exchange_diff_line_balance,
                }
                #print('data', data)
                return data
        elif has_enough_comp_debit or has_enough_comp_credit:
            # Compute the new value for balance.
            balance_after_partial = current_balance + auto_balance
            balance_after_partial_usd = current_balance_usd + auto_balance_usd

            # Get the rate of the original journal item.
            rate = abs(line.source_amount_currency) / abs(line.source_balance)

            # Compute the amounts to make a partial.
            new_line_balance = line.company_currency_id.round(balance_after_partial * abs(line.balance) / abs(current_balance))
            new_line_balance_usd = abs(line.balance_usd) - abs(balance_after_partial_usd)
            exchange_diff_line_balance = balance_after_partial - new_line_balance
            amount_currency_after_partial = line.currency_id.round(new_line_balance * rate)
            return {
                'exchange_diff_line': exchange_diff_line,
                'amount_currency': amount_currency_after_partial,
                'balance': new_line_balance,
                'balance_usd': new_line_balance_usd,
                'exchange_balance': exchange_diff_line_balance,
            }
        return None

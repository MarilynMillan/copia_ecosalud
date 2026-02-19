import logging
from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class BankReconciliationReportCustomHandler(models.AbstractModel):
    _inherit = 'account.bank.reconciliation.report.handler'

    def _bank_reconciliation_report_custom_engine_common(self, options, internal_type, current_groupby, from_last_statement, unreconciled=True):
        """
            Retrieve entries for bank reconciliation based on specified parameters.
            Parameters:
            - options (dict): A dictionary containing options of the report.
            - internal_type (str): The internal type used for classification (e.g., receipt, payment). For the receipt
                                   we will query the entries with a positive amounts and for the payment
                                   the negative amounts.
                                   If the internal type is another thing that receipt or payment it will get all the
                                   entries position or negative
            - current_groupby (str): The current grouping criteria.
            - last_statement (bool, optional): If True, query entries from the last bank statement.
                                               Otherwise, query entries that are not part of the last bank
                                               statement.
            - unreconciled (bool, optional): If True, query the unreconciled entries only

        """
        currency_dif = options['currency_dif']
        journal, journal_currency, _company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return self._build_custom_engine_result()

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def build_result_dict(query_res_lines):
            # The query should find exactly one account move line per bank statement line
            if current_groupby == 'id':
                res = query_res_lines[0]
                foreign_currency = self.env['res.currency'].browse(res['foreign_currency_id'])
                rate = 1  # journal_currency / foreign_currency
                if foreign_currency:
                    rate = (res['amount'] / res['amount_currency']) if res['amount_currency'] else 0

                return self._build_custom_engine_result(
                    date=res['date'] if res['date'] else None,
                    label=res['payment_ref'] or res['ref'] or '/',
                    amount_currency=-res['amount_residual'] if res['foreign_currency_id'] else None,
                    amount_currency_currency_id=foreign_currency.id if res['foreign_currency_id'] else None,
                    currency=foreign_currency.display_name if res['foreign_currency_id'] else None,
                    amount=-res['amount_residual'] * rate if res['amount_residual'] else None,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    rate = 1  # journal_currency / foreign_currency
                    if res['foreign_currency_id']:
                        rate = (res['amount'] / res['amount_currency']) if res['amount_currency'] else 0
                    amount += -res.get('amount_residual', 0) * rate if unreconciled else res.get('amount', 0)

                return self._build_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        tables, where_clause, where_params = report._query_get(options, 'strict_range', domain=[
            ('journal_id', '=', journal.id),
            ('account_id', '=', journal.default_account_id.id),  # There should be only 1 line per move with that account
        ])

        if from_last_statement:
            last_statement_id = self._get_last_bank_statement(journal, options).id
            if last_statement_id:
                last_statement_id_condition = SQL("st_line.statement_id = %s", last_statement_id)
            else:
                # If there is no last statement, the last statement section must be empty and the other must have all
                # transaction
                return self._compute_result([], current_groupby, build_result_dict)
        else:
            last_statement_id_condition = SQL("st_line.statement_id IS NULL")

        if internal_type == 'receipts':
            st_line_amount_condition = SQL("AND st_line.amount > 0")
        elif internal_type == 'payments':
            st_line_amount_condition = SQL("AND st_line.amount < 0")
        else:
            # For the Transaction without statement, the internal type is 'all'
            st_line_amount_condition = SQL("")
        if currency_dif == self.env.company.currency_id.symbol:
            # Build query
            query = SQL(
                """
               SELECT %(select_from_groupby)s,
                      st_line.id,
                      move.name,
                      move.ref,
                      move.date,
                      st_line.payment_ref,
                      st_line.amount,
                      st_line.amount_residual,
                      st_line.amount_currency,
                      st_line.foreign_currency_id
                 FROM %(tables)s
                 JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
                 JOIN account_move move ON move.id = st_line.move_id
                WHERE %(where_clause)s
                      %(is_unreconciled)s
                      %(st_line_amount_condition)s
                  AND %(last_statement_id_condition)s
             GROUP BY %(group_by)s,
                      st_line.id,
                      move.id
                """,
                select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line', current_groupby)) if current_groupby else SQL('null'),
                tables=SQL(tables),
                where_clause=SQL(where_clause, *where_params),
                is_unreconciled=SQL("AND NOT st_line.is_reconciled") if unreconciled else SQL(""),
                st_line_amount_condition=st_line_amount_condition,
                last_statement_id_condition=last_statement_id_condition,
                group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL('st_line.id'),  # Same key in the groupby because we can't put a null key in a group by
            )
        else:
            # Build query
            query = SQL(
                """
               SELECT %(select_from_groupby)s,
                      st_line.id,
                      move.name,
                      move.ref,
                      move.date,
                      st_line.payment_ref,
                      st_line.amount_usd_statement as amount,
                      st_line.balance_usd as amount_residual,
                      st_line.amount_usd_statement as amount_currency,
                      st_line.foreign_currency_id
                 FROM %(tables)s
                 JOIN account_bank_statement_line st_line ON st_line.move_id = account_move_line.move_id
                 JOIN account_move move ON move.id = st_line.move_id
                WHERE %(where_clause)s
                      %(is_unreconciled)s
                      %(st_line_amount_condition)s
                  AND %(last_statement_id_condition)s
             GROUP BY %(group_by)s,
                      st_line.id,
                      move.id
                """,
                select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line',
                                                                             current_groupby)) if current_groupby else SQL(
                    'null'),
                tables=SQL(tables),
                where_clause=SQL(where_clause, *where_params),
                is_unreconciled=SQL("AND NOT st_line.is_reconciled") if unreconciled else SQL(""),
                st_line_amount_condition=st_line_amount_condition,
                last_statement_id_condition=last_statement_id_condition,
                group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL('st_line.id'),
                # Same key in the groupby because we can't put a null key in a group by
            )

        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return self._compute_result(query_res_lines, current_groupby, build_result_dict)

    def _bank_reconciliation_report_custom_engine_outstanding_common(self, options, internal_type, current_groupby):
        """
            This engine retrieves the data of all recorded payments/receipts that have not been matched with a bank
            statement yet
        """
        currency_dif = options['currency_dif']
        journal, journal_currency, company_currency = self._get_bank_journal_and_currencies(options)
        if not journal:
            return self._build_custom_engine_result()

        report = self.env['account.report'].browse(options['report_id'])
        report._check_groupby_fields([current_groupby] if current_groupby else [])

        def build_result_dict(query_res_lines):
            if current_groupby == 'id':
                res = query_res_lines[0]
                convert = not (journal_currency and res['currency_id'] == journal_currency.id)
                amount_currency = res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']
                balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']
                foreign_currency = self.env['res.currency'].browse(res['currency_id'])

                return self._build_custom_engine_result(
                    date=res['date'] if res['date'] else None,
                    label=res['ref'] if res['ref'] else None,
                    amount_currency=amount_currency if convert else None,
                    amount_currency_currency_id=foreign_currency.id if convert else None,
                    currency=foreign_currency.display_name if convert else None,
                    amount=company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to']) if convert else amount_currency,
                    amount_currency_id=journal_currency.id,
                )
            else:
                amount = 0
                for res in query_res_lines:
                    convert = not (journal_currency and res['currency_id'] == journal_currency.id)
                    if convert:
                        balance = res['amount_residual'] if res['is_account_reconcile'] else res['balance']
                        amount += company_currency._convert(balance, journal_currency, journal.company_id, options['date']['date_to'])
                    else:
                        amount += res['amount_residual_currency'] if res['is_account_reconcile'] else res['amount_currency']

                return self._build_custom_engine_result(
                    amount=amount,
                    amount_currency_id=journal_currency.id,
                    has_sublines=bool(len(query_res_lines)),
                )

        accounts = journal._get_journal_inbound_outstanding_payment_accounts() + journal._get_journal_outbound_outstanding_payment_accounts()

        tables, where_clause, where_params = report._query_get(options, 'normal', domain=[
            ('journal_id', '=', journal.id),
            ('account_id', 'in', accounts.ids),
            ('full_reconcile_id', '=', False),
            ('amount_residual_currency', '!=', 0.0)
        ])
        if currency_dif == self.env.company.currency_id.symbol:
            # Build query
            query = SQL(
                """
               SELECT %(select_from_groupby)s,
                      account_move_line.account_id,
                      account_move_line.payment_id,
                      account_move_line.move_id,
                      account_move_line.currency_id,
                      account_move_line.move_name AS name,
                      account_move_line.ref,
                      account_move_line.date,
                      account.reconcile AS is_account_reconcile,
                      SUM(account_move_line.amount_residual) AS amount_residual,
                      SUM(account_move_line.balance) AS balance,
                      SUM(account_move_line.amount_residual_currency) AS amount_residual_currency,
                      SUM(account_move_line.amount_currency) AS amount_currency
                 FROM %(tables)s
                 JOIN account_account account ON account.id = account_move_line.account_id
                WHERE %(where_clause)s
                  AND %(is_receipt)s
             GROUP BY %(group_by)s,
                      account_move_line.account_id,
                      account_move_line.payment_id,
                      account_move_line.move_id,
                      account_move_line.currency_id,
                      account_move_line.move_name,
                      account_move_line.ref,
                      account_move_line.date,
                      account.reconcile
               """,
                select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line', current_groupby)) if current_groupby else SQL('null'),
                tables=SQL(tables),
                where_clause=SQL(where_clause, *where_params),
                is_receipt=SQL("account_move_line.balance > 0") if internal_type == "receipts" else SQL("account_move_line.balance < 0"),
                group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL('account_move_line.account_id'),  # Same key in the groupby because we can't put a null key in a group by
            )
        else:
            # Build query
            query = SQL(
                """
               SELECT %(select_from_groupby)s,
                      account_move_line.account_id,
                      account_move_line.payment_id,
                      account_move_line.move_id,
                      account_move_line.currency_id,
                      account_move_line.move_name AS name,
                      account_move_line.ref,
                      account_move_line.date,
                      account.reconcile AS is_account_reconcile,
                      SUM(account_move_line.amount_residual_usd) AS amount_residual,
                      SUM(account_move_line.balance_usd) AS balance,
                      SUM(account_move_line.amount_residual_usd) AS amount_residual_currency,
                      SUM(account_move_line.balance_usd) AS amount_currency
                 FROM %(tables)s
                 JOIN account_account account ON account.id = account_move_line.account_id
                WHERE %(where_clause)s
                  AND %(is_receipt)s
             GROUP BY %(group_by)s,
                      account_move_line.account_id,
                      account_move_line.payment_id,
                      account_move_line.move_id,
                      account_move_line.currency_id,
                      account_move_line.move_name,
                      account_move_line.ref,
                      account_move_line.date,
                      account.reconcile
               """,
                select_from_groupby=SQL("%s AS grouping_key", SQL.identifier('account_move_line',
                                                                             current_groupby)) if current_groupby else SQL(
                    'null'),
                tables=SQL(tables),
                where_clause=SQL(where_clause, *where_params),
                is_receipt=SQL("account_move_line.balance_usd > 0") if internal_type == "receipts" else SQL(
                    "account_move_line.balance_usd < 0"),
                group_by=SQL.identifier('account_move_line', current_groupby) if current_groupby else SQL(
                    'account_move_line.account_id'),
                # Same key in the groupby because we can't put a null key in a group by
            )
        self._cr.execute(query)
        query_res_lines = self._cr.dictfetchall()

        return self._compute_result(query_res_lines, current_groupby, build_result_dict)
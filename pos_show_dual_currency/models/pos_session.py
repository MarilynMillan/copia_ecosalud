# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, AccessError, UserError
from odoo.tools import float_is_zero


class PosSession(models.Model):
    _inherit = "pos.session"

    # =========================
    # Dual currency (reference)
    # =========================
    tax_today = fields.Float(
        string="Tasa Sesión",
        store=True,
        compute="_compute_tax_today",
        digits="Dual_Currency_rate",
        help="Factor para convertir montos de la moneda de la sesión a la moneda de referencia.",
    )

    ref_me_currency_id = fields.Many2one(
        "res.currency",
        related="config_id.show_currency",
        string="Reference Currency",
        store=False,
        readonly=True,
    )

    # Cash control (reference currency)
    cash_register_balance_start_mn_ref = fields.Monetary(
        string="Reference Starting Balance",
        currency_field="ref_me_currency_id",
        readonly=True,
    )
    cash_register_balance_end_real_mn_ref = fields.Monetary(
        string="Reference Ending Balance",
        currency_field="ref_me_currency_id",
        readonly=True,
    )
    cash_register_total_entry_encoding_ref = fields.Monetary(
        compute="_compute_cash_balance_ref",
        string="Ref Total Cash Transaction",
        currency_field="ref_me_currency_id",
        readonly=True,
    )
    cash_register_balance_end_ref = fields.Monetary(
        compute="_compute_cash_balance_ref",
        string="Ref Theoretical Closing Balance",
        currency_field="ref_me_currency_id",
        readonly=True,
        help="Opening balance + movimientos de efectivo (ref).",
    )
    cash_register_difference_ref = fields.Monetary(
        compute="_compute_cash_balance_ref",
        string="Ref Before Closing Difference",
        currency_field="ref_me_currency_id",
        readonly=True,
        help="Diferencia entre el balance teórico (ref) y el real (ref).",
    )
    cash_real_transaction_ref = fields.Monetary(
        string="Ref Transaction",
        currency_field="ref_me_currency_id",
        readonly=True,
        help="Suma de movimientos reales (ref) al cerrar sesión.",
    )

    me_ref_cash_journal_id = fields.Many2one(
        "account.journal",
        string="Ref Cash Journal",
        compute="_compute_ref_cash_journal",
        store=True,
    )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _get_main_statement_lines(self):
        """Statement lines that belong to the main cash journal."""
        self.ensure_one()
        if not self.cash_journal_id:
            return self.env["account.bank.statement.line"]
        return self.sudo().statement_line_ids.filtered(lambda l: l.journal_id == self.cash_journal_id)

    def _get_ref_statement_lines(self):
        """Statement lines that belong to the reference cash journal."""
        self.ensure_one()
        if not self.me_ref_cash_journal_id:
            return self.env["account.bank.statement.line"]
        return self.sudo().statement_line_ids.filtered(lambda l: l.journal_id == self.me_ref_cash_journal_id)

    # ---------------------------------------------------------
    # Compute / Overrides (Odoo 17)
    # ---------------------------------------------------------
    @api.depends("config_id.show_currency_rate")
    def _compute_tax_today(self):
        for rec in self:
            rate = rec.config_id.show_currency_rate or 0.0
            rec.tax_today = 1.0 / rate if rate > 0 else 1.0

    @api.depends("config_id", "payment_method_ids", "payment_method_ids.journal_id", "payment_method_ids.currency_id")
    def _compute_cash_journal(self):
        """
        Odoo 17 escoge el primer método 'cash'. Con dual currency, queremos que el cash_journal_id
        sea el de la moneda de la sesión (no el de referencia) para que los cálculos estándar no
        se contaminen con los movimientos ref.
        """
        for session in self:
            main_cash_pm = session.payment_method_ids.filtered(
                lambda pm: pm.is_cash_count and (not pm.currency_id or pm.currency_id == session.currency_id)
            )[:1]
            session.cash_journal_id = main_cash_pm.journal_id

    @api.depends("config_id", "payment_method_ids", "payment_method_ids.journal_id", "payment_method_ids.currency_id")
    def _compute_ref_cash_journal(self):
        for session in self:
            session.me_ref_cash_journal_id = False
            if not session.ref_me_currency_id:
                continue
            ref_cash_pm = session.payment_method_ids.filtered(
                lambda pm: pm.is_cash_count and pm.currency_id == session.ref_me_currency_id
            )[:1]
            session.me_ref_cash_journal_id = ref_cash_pm.journal_id

    @api.depends(
        "payment_method_ids",
        "order_ids",
        "cash_register_balance_start",
        "statement_line_ids.amount",
        "statement_line_ids.journal_id",
        "state",
    )
    def _compute_cash_balance(self):
        """
        Copia del compute estándar de Odoo 17 pero filtrando statement_line_ids por cash_journal_id.
        Esto evita que los movimientos en journal ref alteren los balances estándar.
        """
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered("is_cash_count")[:1]
            if cash_payment_method and session.cash_journal_id:
                last_session = session.search(
                    [("config_id", "=", session.config_id.id), ("id", "<", session.id)], limit=1
                )
                result = self.env["pos.payment"]._read_group(
                    [("session_id", "=", session.id), ("payment_method_id", "=", cash_payment_method.id)],
                    aggregates=["amount:sum"],
                )
                total_cash_payment = (result[0][0] if result else 0.0) or 0.0

                statement_amount = sum(session._get_main_statement_lines().mapped("amount"))
                if session.state == "closed":
                    # al cerrar, Odoo usa cash_real_transaction (ya calculado en _validate_session)
                    session.cash_register_total_entry_encoding = (session.cash_real_transaction or 0.0) + total_cash_payment
                else:
                    session.cash_register_total_entry_encoding = statement_amount + total_cash_payment

                session.cash_register_balance_end = (last_session.cash_register_balance_end_real or 0.0) + session.cash_register_total_entry_encoding
                session.cash_register_difference = (session.cash_register_balance_end_real or 0.0) - session.cash_register_balance_end
            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0

    @api.depends(
        "payment_method_ids",
        "order_ids",
        "cash_register_balance_start_mn_ref",
        "cash_register_balance_end_real_mn_ref",
        "statement_line_ids.amount",
        "statement_line_ids.journal_id",
        "state",
    )
    def _compute_cash_balance_ref(self):
        for session in self:
            if not session.me_ref_cash_journal_id or not session.ref_me_currency_id:
                session.cash_register_total_entry_encoding_ref = 0.0
                session.cash_register_balance_end_ref = 0.0
                session.cash_register_difference_ref = 0.0
                continue

            last_session = session.search(
                [("config_id", "=", session.config_id.id), ("id", "<", session.id)], limit=1
            )

            # Total pagos en moneda ref (usando amount_ref guardado en pos.payment)
            ref_cash_pm = session.payment_method_ids.filtered(
                lambda pm: pm.is_cash_count and pm.currency_id == session.ref_me_currency_id
            )[:1]
            total_ref_payments = 0.0
            if ref_cash_pm:
                res = self.env["pos.payment"]._read_group(
                    [("session_id", "=", session.id), ("payment_method_id", "=", ref_cash_pm.id)],
                    aggregates=["amount_ref:sum"],
                )
                total_ref_payments = (res[0][0] if res else 0.0) or 0.0

            statement_amount_ref = sum(session._get_ref_statement_lines().mapped("amount"))

            if session.state == "closed":
                session.cash_register_total_entry_encoding_ref = (session.cash_real_transaction_ref or 0.0) + total_ref_payments
            else:
                session.cash_register_total_entry_encoding_ref = statement_amount_ref + total_ref_payments

            session.cash_register_balance_end_ref = (last_session.cash_register_balance_end_real_mn_ref or 0.0) + session.cash_register_total_entry_encoding_ref
            session.cash_register_difference_ref = (session.cash_register_balance_end_real_mn_ref or 0.0) - session.cash_register_balance_end_ref

    def action_pos_session_open(self):
        res = super().action_pos_session_open()
        for session in self.filtered(lambda s: s.state == "opened"):
            if session.config_id.cash_control and not session.rescue:
                last_session = self.search(
                    [("config_id", "=", session.config_id.id), ("id", "<", session.id)], limit=1
                )
                session.cash_register_balance_start_mn_ref = last_session.cash_register_balance_end_real_mn_ref or 0.0
        return res

    def _post_statement_difference_ref(self, amount, is_opening):
        """Igual que _post_statement_difference pero en journal ref + currency_id ref."""
        self.ensure_one()
        if not amount or not self.me_ref_cash_journal_id or not self.ref_me_currency_id:
            return

        if not self.config_id.cash_control:
            return

        date = self._get_main_statement_lines().sorted()[-1:].date or fields.Date.context_today(self)
        st_line_vals = {
            "journal_id": self.me_ref_cash_journal_id.id,
            "amount": amount,
            "date": date,
            "pos_session_id": self.id,
            "currency_id": self.ref_me_currency_id.id,
        }

        if amount < 0.0:
            if not self.me_ref_cash_journal_id.loss_account_id:
                raise UserError(
                    _(
                        "Please go on the %s journal and define a Loss Account. "
                        "This account will be used to record cash difference.",
                        self.me_ref_cash_journal_id.name,
                    )
                )
            st_line_vals["payment_ref"] = _("Cash difference observed during the counting (Loss)") + (
                _(" - opening") if is_opening else _(" - closing")
            )
            if not is_opening:
                st_line_vals["counterpart_account_id"] = self.me_ref_cash_journal_id.loss_account_id.id
        else:
            if not self.me_ref_cash_journal_id.profit_account_id:
                raise UserError(
                    _(
                        "Please go on the %s journal and define a Profit Account. "
                        "This account will be used to record cash difference.",
                        self.me_ref_cash_journal_id.name,
                    )
                )
            st_line_vals["payment_ref"] = _("Cash difference observed during the counting (Profit)") + (
                _(" - opening") if is_opening else _(" - closing")
            )
            if not is_opening:
                st_line_vals["counterpart_account_id"] = self.me_ref_cash_journal_id.profit_account_id.id

        self.env["account.bank.statement.line"].create(st_line_vals)

    def set_cashbox_pos_usd(self, cashbox_value, notes=None):
        """Opening cash control para la moneda de referencia (USD)."""
        self.ensure_one()
        if not self.me_ref_cash_journal_id:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        difference = cashbox_value - (self.cash_register_balance_start_mn_ref or 0.0)
        self.cash_register_balance_start_mn_ref = cashbox_value
        self.sudo()._post_statement_difference_ref(difference, True)
        self._post_cash_details_message_usd("Opening", difference, notes or "")

    def _post_cash_details_message_usd(self, state, difference, notes):
        self.ensure_one()
        message = ""
        cur = self.ref_me_currency_id
        if difference:
            symbol_before = f"{cur.symbol} " if cur.position == "before" else ""
            symbol_after = f"{cur.symbol}" if cur.position == "after" else ""
            message = f"{state} difference: {symbol_before}{cur.round(difference)} {symbol_after}<br/>"
        if notes:
            message += (notes or "").replace("\n", "<br/>")
        if message:
            self.message_post(body=message)

    def try_cash_in_out_ref_currency(self, _type, amount, reason, extras, currency_ref=None):
        """Cash in/out en moneda ref."""
        sign = 1 if _type == "in" else -1
        sessions = self.filtered("me_ref_cash_journal_id")
        if not sessions:
            raise UserError(_("There is no cash payment method for this PoS Session"))

        self.env["account.bank.statement.line"].create(
            [
                {
                    "pos_session_id": session.id,
                    "journal_id": session.me_ref_cash_journal_id.id,
                    "amount": sign * amount,
                    "date": fields.Date.context_today(self),
                    "payment_ref": "-".join([session.name, extras.get("translatedType", ""), reason or ""]).strip("-"),
                    "currency_id": session.ref_me_currency_id.id,
                }
                for session in sessions
            ]
        )

        message_content = [f"Cash {extras.get('translatedType', '')}", f"- Amount: {extras.get('formattedAmount', amount)}"]
        if reason:
            message_content.append(f"- Reason: {reason}")
        self.message_post(body="<br/>\n".join(message_content))

    def post_closing_cash_details_ref(self, counted_cash):
        """Guardar el efectivo contado en ref (se llama desde el UI)."""
        self.ensure_one()
        if not self.me_ref_cash_journal_id:
            raise UserError(_("There is no Ref cash register in this session."))
        self.cash_register_balance_end_real_mn_ref = counted_cash
        return {"successful": True}

    def update_closing_control_state_session_ref(self, notes=None):
        self.ensure_one()
        self._post_cash_details_message_usd("Closing", self.cash_register_difference_ref, notes or "")

    # ------------------------------------------------------------------
    # POS UI data: currency ref
    # ------------------------------------------------------------------
    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        # Ensure that res.currency is loaded (usually it is), but we need to load currency_ref specifically?
        # In v17, models like res.currency are loaded. We just need to make sure we append our data.
        # Actually, we can just overload _load_pos_data to inject 'res_currency_ref'.
        return result

    def _loader_params_res_currency(self):
        # We can try to extend parameters if needed, but here we want a specific separate key in loaded_data
        return super()._loader_params_res_currency()

    def _get_pos_ui_res_currency_ref(self):
        currency_id = self.ref_me_currency_id.id or self.company_id.currency_id.id
        domain = [("id", "=", currency_id)]
        fields = ["id", "name", "symbol", "position", "rounding", "rate", "decimal_places"]
        res_currency = self.env["res.currency"].search_read(domain, fields)
        return res_currency[0] if res_currency else False

    @api.model
    def _load_pos_data(self, data):
        loaded_data = super()._load_pos_data(data)
        # Inject res_currency_ref
        # Note: 'self' here is the model, not a record. We need the session context.
        # _load_pos_data(self, data)
        # Wait, how do we get the session ID?
        # In v17, _load_pos_data is called on the model. It receives 'data' which might contain session info?
        # Actually, usually session_id is passed in context or data.
        # But wait, self.env.user...
        # Let's look at how _load_pos_data works in 17.
        # def _load_pos_data(self, data):
        #     domain = self._loader_params_pos_session()['search_params']['domain']
        #     pos_session = self.search(domain)
        # Ah, typically load_pos_data is called by the controller which passes domain/fields.
        # But here we are overriding the method on the model.
        # The session is typically retrieved via domain in data? No.
        # Let's check knowledgebase for _load_pos_data signature.
        # Knowledgebase lookup...
        # Assuming standard v17 pattern:
        # We can rely on `self.env['pos.session'].search([('state', '=', 'opening_control')])` or similar? No.

        # Actually, in v17, the controller calls:
        # session_info = request.env['pos.session'].browse(session_id).get_pos_ui_product_category(...)
        # No, it calls `models._load_pos_data(data)`.

        # Let's stick to the previous pattern using `_pos_data_process` if it exists in v17?
        # `_pos_data_process` was v16.
        # In v17 it is `_load_pos_data`.

        # However, to avoid complexity if I'm not sure about getting the session instance inside the class method:
        # I can see `pos.session` fields are loaded.
        # I added `cash_register_balance_start_mn_ref` to `pos.session` loader params via `_loader_params_pos_session` override (if that still works).
        # Does `_loader_params_pos_session` work in v17?
        # Point of Sale `pos_session.py` in v17 DOES define `_loader_params_pos_session`.
        # So overrides to `_loader_params_...` ARE valid in v17 for core models.
        pass
        return loaded_data

    # Re-adding the loader params methods as they ARE valid in v17 for core models loaded via _load_pos_data loop.

    @api.model
    def _loader_params_pos_session(self):
        params = super()._loader_params_pos_session()
        # params['search_params']['fields'].append('cash_register_balance_start_mn_ref')
        # But 'search_params' might be missing if super doesn't return it structured that way?
        # V17 structure: {'search_params': {'domain': ..., 'fields': [...]}}
        if params and 'search_params' in params and 'fields' in params['search_params']:
             params['search_params']['fields'].append('cash_register_balance_start_mn_ref')
        return params

    @api.model
    def _loader_params_pos_payment_method(self):
        params = super()._loader_params_pos_payment_method()
        if params and 'search_params' in params and 'fields' in params['search_params']:
             params['search_params']['fields'].append('currency_id')
        return params

    # For res_currency_ref, we need to inject it manually into the response because it's not a standard loaded model list item
    # or we can treat it as part of 'res.currency' load but we want a specific key 'res_currency_ref'.

    @api.model
    def _load_pos_data(self, data):
        loaded_data = super()._load_pos_data(data)
        # We need the session.
        # The session is loaded in loaded_data['pos.session']['data'][0] usually.
        session_data = loaded_data.get('pos.session', {}).get('data', [])
        if session_data:
            session_id = session_data[0]['id']
            session = self.browse(session_id)
            # Fetch ref currency
            loaded_data['res_currency_ref'] = session._get_pos_ui_res_currency_ref()
        return loaded_data

    # ------------------------------------------------------------------
    # Closing control UI: include ref cashbox details
    # ------------------------------------------------------------------
    def get_closing_control_data(self):
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("You don't have the access rights to get the point of sale closing control data."))
        self.ensure_one()

        orders = self._get_closed_orders()
        payments = orders.payment_ids.filtered(lambda p: p.payment_method_id.type != "pay_later")
        last_session = self.search([("config_id", "=", self.config_id.id), ("id", "<", self.id)], limit=1)

        # MAIN cash method (session currency)
        main_cash_pms = self.payment_method_ids.filtered(
            lambda pm: pm.type == "cash" and (not pm.currency_id or pm.currency_id == self.currency_id)
        )
        main_cash_pm = main_cash_pms[0] if main_cash_pms else None
        total_main_cash_payments = (
            sum(payments.filtered(lambda p: p.payment_method_id == main_cash_pm).mapped("amount")) if main_cash_pm else 0.0
        )

        # REF cash method
        ref_cash_pms = self.payment_method_ids.filtered(lambda pm: pm.type == "cash" and pm.currency_id == self.ref_me_currency_id)
        ref_cash_pm = ref_cash_pms[0] if ref_cash_pms else None
        total_ref_cash_payments = (
            sum(payments.filtered(lambda p: p.payment_method_id == ref_cash_pm).mapped("amount_ref")) if ref_cash_pm else 0.0
        )

        def _build_moves(lines):
            cash_in_count = 0
            cash_out_count = 0
            res = []
            for cash_move in lines.sorted("create_date"):
                if cash_move.amount > 0:
                    cash_in_count += 1
                    name = f"Cash in {cash_in_count}"
                else:
                    cash_out_count += 1
                    name = f"Cash out {cash_out_count}"
                res.append({"name": cash_move.payment_ref if cash_move.payment_ref else name, "amount": cash_move.amount})
            return res

        main_lines = self._get_main_statement_lines()
        ref_lines = self._get_ref_statement_lines()

        default_cash_details = {
            "name": main_cash_pm.name if main_cash_pm else None,
            "amount": (last_session.cash_register_balance_end_real or 0.0)
                      + total_main_cash_payments
                      + sum(main_lines.mapped("amount")),
            "opening": last_session.cash_register_balance_end_real or 0.0,
            "payment_amount": total_main_cash_payments,
            "moves": _build_moves(main_lines),
            "id": main_cash_pm.id if main_cash_pm else None,
        } if main_cash_pm else None

        default_cash_details_ref = {
            "name": ref_cash_pm.name if ref_cash_pm else None,
            "amount": (last_session.cash_register_balance_end_real_mn_ref or 0.0)
                      + total_ref_cash_payments
                      + sum(ref_lines.mapped("amount")),
            "opening": last_session.cash_register_balance_end_real_mn_ref or 0.0,
            "payment_amount": total_ref_cash_payments,
            "moves": _build_moves(ref_lines),
            "id": ref_cash_pm.id if ref_cash_pm else None,
        } if ref_cash_pm else None

        excluded = self.env["pos.payment.method"]
        if main_cash_pm:
            excluded |= main_cash_pm
        if ref_cash_pm:
            excluded |= ref_cash_pm
        other_payment_method_ids = self.payment_method_ids - excluded

        if default_cash_details is not None:
            default_cash_details["default_cash_details_ref"] = default_cash_details_ref

        return {
            "orders_details": {"quantity": len(orders), "amount": sum(orders.mapped("amount_total"))},
            "opening_notes": self.opening_notes,
            "default_cash_details": default_cash_details,
            "other_payment_methods": [
                {
                    "name": pm.name,
                    "amount": sum(orders.payment_ids.filtered(lambda p: p.payment_method_id == pm).mapped("amount")),
                    "number": len(orders.payment_ids.filtered(lambda p: p.payment_method_id == pm)),
                    "id": pm.id,
                    "type": pm.type,
                }
                for pm in other_payment_method_ids
            ],
            "is_manager": self.user_has_groups("point_of_sale.group_pos_manager"),
            "amount_authorized_diff": self.config_id.amount_authorized_dif if self.config_id.set_maximum_difference else None,
            "amount_authorized_diff_ref": self.config_id.amount_authorized_diff_ref if self.config_id.set_maximum_difference else None,
        }

    # ------------------------------------------------------------------
    # Closing: add posting of ref cash differences and isolate statement lines
    # ------------------------------------------------------------------
    def _validate_session(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """Rebase sobre Odoo 17: añade posting de diferencia ref y evita mezclar journals."""
        from odoo.exceptions import AccessError

        bank_payment_method_diffs = bank_payment_method_diffs or {}
        self.ensure_one()
        data = {}
        sudo = self.user_has_groups("point_of_sale.group_pos_user")

        main_lines = self._get_main_statement_lines()
        ref_lines = self._get_ref_statement_lines()

        if self.order_ids.filtered(lambda o: o.state != "cancel") or main_lines or ref_lines:
            self.cash_real_transaction = sum(main_lines.mapped("amount"))
            self.cash_real_transaction_ref = sum(ref_lines.mapped("amount"))

            if self.state == "closed":
                raise UserError(_("This session is already closed."))
            self._check_if_no_draft_orders()
            self._check_invoices_are_posted()

            cash_difference_before_statements = self.cash_register_difference
            cash_difference_ref_before_statements = self.cash_register_difference_ref

            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
                self._get_closed_orders().filtered(lambda o: not o.is_total_cost_computed)._compute_total_cost_at_session_closing(
                    self.picking_ids.move_ids
                )
            try:
                with self.env.cr.savepoint():
                    data = (
                        self.with_company(self.company_id)
                        .with_context(check_move_validity=False, skip_invoice_sync=True)
                        ._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                    )
            except AccessError as e:
                if sudo:
                    data = (
                        self.sudo()
                        .with_company(self.company_id)
                        .with_context(check_move_validity=False, skip_invoice_sync=True)
                        ._create_account_move(balancing_account, amount_to_balance, bank_payment_method_diffs)
                    )
                else:
                    raise e

            balance = sum(self.move_id.line_ids.mapped("balance"))
            try:
                with self.move_id._check_balanced({"records": self.move_id.sudo()}):
                    pass
            except UserError:
                self.env.cr.rollback()
                return self._close_session_action(balance)

            # post cash differences
            self.sudo()._post_statement_difference(cash_difference_before_statements, False)
            self.sudo()._post_statement_difference_ref(cash_difference_ref_before_statements, False)

            if self.move_id.line_ids:
                self.move_id.sudo().with_company(self.company_id)._post()
                for dummy, amount_data in data["sales"].items():
                    self.env["account.move.line"].browse(amount_data["move_line_id"]).sudo().with_company(self.company_id).write(
                        {
                            "price_subtotal": abs(amount_data["amount_converted"]),
                            "price_total": abs(amount_data["amount_converted"]) + abs(amount_data["tax_amount"]),
                        }
                    )
                self.env["pos.order"].search([("session_id", "=", self.id), ("state", "=", "paid")]).write({"state": "done"})
            else:
                self.move_id.sudo().unlink()

            self.sudo().with_company(self.company_id)._reconcile_account_move_lines(data)
        else:
            self.sudo()._post_statement_difference(self.cash_register_difference, False)
            self.sudo()._post_statement_difference_ref(self.cash_register_difference_ref, False)

        self.write({"state": "closed"})
        return True

    # ------------------------------------------------------------------
    # Accounting helpers with currency conversion (kept from your v16)
    # ------------------------------------------------------------------
    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        MoveLine = data.get("MoveLine")
        split_receivables_cash = data.get("split_receivables_cash")
        combine_receivables_cash = data.get("combine_receivables_cash")

        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id.id
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(journal_id, amounts["amount"], payment)
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(payment, amounts["amount"], amounts["amount_converted"])
            )

        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        for payment_method, amounts in combine_receivables_cash.items():
            if not float_is_zero(amounts["amount"], precision_rounding=self.currency_id.rounding):
                amount = amounts["amount"]
                if payment_method.currency_id and payment_method.currency_id != self.company_id.currency_id:
                    amount = amount * (self.config_id.show_currency_rate or 1.0)

                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(payment_method.journal_id.id, amount, payment_method)
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals(payment_method, amount, amounts["amount_converted"])
                )

        BankStatementLine = self.env["account.bank.statement.line"]
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped("move_id.line_ids").filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped("move_id.line_ids").filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)

        data.update(
            {
                "split_cash_statement_lines": split_cash_statement_lines,
                "combine_cash_statement_lines": combine_cash_statement_lines,
                "split_cash_receivable_lines": split_cash_receivable_lines,
                "combine_cash_receivable_lines": combine_cash_receivable_lines,
            }
        )
        return data

    def _create_bank_payment_moves(self, data):
        combine_receivables_bank = data.get("combine_receivables_bank")
        split_receivables_bank = data.get("split_receivables_bank")
        bank_payment_method_diffs = data.get("bank_payment_method_diffs")
        MoveLine = data.get("MoveLine")
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}

        for payment_method, amounts in combine_receivables_bank.items():
            combine_receivable_line = MoveLine.create(
                self._get_combine_receivable_vals(payment_method, amounts["amount"], amounts["amount_converted"])
            )

            amount = amounts["amount"]
            amount_converted = amounts["amount_converted"]
            if payment_method.currency_id and payment_method.currency_id != self.company_id.currency_id:
                rate = self.config_id.show_currency_rate or 1.0
                amount = amount * rate
                amount_converted = amount_converted * rate

            amounts["amount"] = amount
            amounts["amount_converted"] = amount_converted

            payment_receivable_line = self._create_combine_account_payment(
                payment_method, amounts, diff_amount=bank_payment_method_diffs.get(payment_method.id) or 0
            )
            payment_method_to_receivable_lines[payment_method] = combine_receivable_line | payment_receivable_line

        for payment, amounts in split_receivables_bank.items():
            split_receivable_line = MoveLine.create(
                self._get_split_receivable_vals(payment, amounts["amount"], amounts["amount_converted"])
            )

            amount = amounts["amount"]
            amount_converted = amounts["amount_converted"]
            if payment.currency_id and payment.currency_id != self.company_id.currency_id:
                rate = self.config_id.show_currency_rate or 1.0
                amount = amount * rate
                amount_converted = amount_converted * rate

            amounts["amount"] = amount
            amounts["amount_converted"] = amount_converted

            payment_receivable_line = self._create_split_account_payment(payment, amounts)
            payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line

        for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == "bank" and pm.split_transactions):
            self._create_diff_account_move_for_split_payment_method(
                bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0
            )

        data["payment_method_to_receivable_lines"] = payment_method_to_receivable_lines
        data["payment_to_receivable_lines"] = payment_to_receivable_lines
        return data

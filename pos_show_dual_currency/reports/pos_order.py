# -*- coding: utf-8 -*-
import logging
from datetime import timedelta
from collections import defaultdict

import pytz

from odoo import api, fields, models, _
from odoo.osv.expression import AND

_logger = logging.getLogger(__name__)


class ReportSaleDetails(models.AbstractModel):
    _inherit = "report.point_of_sale.report_saledetails"

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        # Mantén el resultado estándar de Odoo (total_paid, etc.)
        data = super().get_sale_details(date_start, date_stop, config_ids, session_ids)

        sessions = self.env['pos.session'].browse(session_ids or [])
        rate_today = sessions[:1].tax_today or 1  # tax_today = 1/show_currency_rate (según tu módulo)
        currency_ref = (sessions[:1].config_id.show_currency
                        or self.env['res.currency'].search([('name', '=', 'USD')], limit=1))


        values_data, sessions = self._get_dual_currency_data(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=session_ids,
        )

        # Determinar moneda ref (preferimos company.currency_id_dif si existe)
        currency_ref = getattr(self.env.company, "currency_id_dif", False) or (sessions[:1].ref_me_currency_id if sessions else False)
        if not currency_ref:
            currency_ref = self.env.company.currency_id

        # rate_today: solo es “representativo” si es 1 sesión
        rate_today = 1.0
        if sessions and len(sessions) == 1 and sessions.tax_today:
            rate_today = sessions.tax_today

        data.update({
            "currency_precision_ref": currency_ref.decimal_places,
            "total_paid_ref": currency_ref.round(values_data["total_paid_ref"]),
            "symbol_ref": currency_ref.symbol,
            "symbol": self.env.company.currency_id.symbol,
            "rate_today": rate_today,
            "products": values_data["products"],
            "payments": values_data["payments"],
            "taxes": values_data["taxes"],
        })

        data['currency_ref'] = {
            'symbol': currency_ref.symbol,
            'position': True if currency_ref.position == 'after' else False,
            'precision': currency_ref.decimal_places,
        }
        return data

    # -------------------------------------------------------------------------
    # Dual currency computation (Odoo 17-safe)
    # -------------------------------------------------------------------------
    def _normalize_session_ids(self, session_ids):
        """session_ids puede venir como recordset, lista, int, False."""
        if not session_ids:
            return []
        if isinstance(session_ids, models.BaseModel):
            return session_ids.ids
        if isinstance(session_ids, (list, tuple, set)):
            return list(session_ids)
        if isinstance(session_ids, int):
            return [session_ids]
        return []

    def _get_dual_currency_data(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        session_ids = self._normalize_session_ids(session_ids)
        sessions = self.env["pos.session"].browse(session_ids).exists() if session_ids else self.env["pos.session"]

        domain = [("state", "in", ["paid", "invoiced", "done"])]

        if session_ids:
            domain = AND([domain, [("session_id", "in", session_ids)]])
        else:
            # Fecha inicio/fin igual que tu lógica, pero usando to_datetime (Odoo 17-friendly)
            user_tz = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")

            if date_start:
                date_start_dt = fields.Datetime.to_datetime(date_start)
            else:
                # hoy 00:00:00 en tz usuario -> UTC
                today = fields.Date.context_today(self)
                date_start_dt = user_tz.localize(fields.Datetime.to_datetime(today)).astimezone(pytz.UTC)

            if date_stop:
                date_stop_dt = fields.Datetime.to_datetime(date_stop)
                if date_stop_dt < date_start_dt:
                    date_stop_dt = date_start_dt + timedelta(days=1, seconds=-1)
            else:
                date_stop_dt = date_start_dt + timedelta(days=1, seconds=-1)

            domain = AND([domain, [
                ("date_order", ">=", fields.Datetime.to_string(date_start_dt)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop_dt)),
            ]])

            if config_ids:
                domain = AND([domain, [("config_id", "in", config_ids)]])

        orders = self.env["pos.order"].search(domain)

        user_currency = self.env.company.currency_id
        total_ref = 0.0
        products_sold = defaultdict(float)
        taxes = {}

        for order in orders:
            # Total ref directo desde tus campos computados por sesión
            total_ref += (order.amount_total_ref or 0.0)

            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.price_unit_ref, line.discount)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                        currency,
                        line.qty,
                        product=line.product_id,
                        partner=line.order_id.partner_id or False,
                    )
                    for tax in line_taxes["taxes"]:
                        taxes.setdefault(tax["id"], {
                            "name": tax["name"],
                            "tax_amount": 0.0,
                            "base_amount": 0.0,
                            "tax_amount_ref": 0.0,
                            "base_amount_ref": 0.0,
                        })
                        taxes[tax["id"]]["tax_amount"] += tax["amount"]
                        taxes[tax["id"]]["base_amount"] += tax["base"]

                        if order.session_rate:
                            taxes[tax["id"]]["tax_amount_ref"] += tax["amount"] / order.session_rate
                            taxes[tax["id"]]["base_amount_ref"] += tax["base"] / order.session_rate
                else:
                    taxes.setdefault(0, {
                        "name": _("No Taxes"),
                        "tax_amount": 0.0,
                        "base_amount": 0.0,
                        "tax_amount_ref": 0.0,
                        "base_amount_ref": 0.0,
                    })
                    taxes[0]["base_amount"] += line.price_subtotal_incl
                    taxes[0]["base_amount_ref"] += (line.price_subtotal_incl_ref or 0.0)

        # Payments: sum(amount) y sum(amount_ref)
        payment_ids = self.env["pos.payment"].search([("pos_order_id", "in", orders.ids)]).ids
        payments = []
        if payment_ids:
            self.env.cr.execute(
                """
                SELECT
                    COALESCE(method.name->>%s, method.name->>'en_US') AS name,
                    SUM(payment.amount) AS total,
                    SUM(payment.amount_ref) AS total_ref
                FROM pos_payment payment
                JOIN pos_payment_method method ON payment.payment_method_id = method.id
                WHERE payment.id = ANY(%s)
                GROUP BY method.id, name
                ORDER BY name
                """,
                (self.env.lang, payment_ids),
            )
            payments = self.env.cr.dictfetchall()

        products = sorted([{
            "product_id": product.id,
            "product_name": product.name,
            "code": product.default_code,
            "quantity": qty,
            "price_unit": price_unit,
            "price_unit_ref": price_unit_ref,
            "discount": discount,
            "uom": product.uom_id.name,
        } for (product, price_unit, price_unit_ref, discount), qty in products_sold.items()],
            key=lambda l: l["product_name"]
        )

        return ({
            "total_paid_ref": total_ref,
            "taxes": list(taxes.values()),
            "payments": payments,
            "products": products,
        }, sessions)
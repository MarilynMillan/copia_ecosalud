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
        # Obtener data base de Odoo
        data = super().get_sale_details(date_start, date_stop, config_ids, session_ids)

        # Normalizar y obtener sesiones
        s_ids = self._normalize_session_ids(session_ids)
        sessions = self.env['pos.session'].browse(s_ids).exists()

        # Obtener data de moneda dual
        values_data, sessions_found = self._get_dual_currency_data(
            date_start=date_start,
            date_stop=date_stop,
            config_ids=config_ids,
            session_ids=s_ids,
        )

        # Definir moneda de referencia (USD por defecto en Venezuela)
        currency_ref = (sessions[:1].config_id.show_currency 
                        or getattr(self.env.company, "currency_id_dif", False)
                        or self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                        or self.env.company.currency_id)

        rate_today = 1.0
        if sessions and len(sessions) == 1:
            # Usamos el campo de tu módulo para la tasa
            rate_today = getattr(sessions, 'tax_today', 1.0)

        # Actualizar diccionario de retorno
        data.update({
            "currency_ref": {
                'symbol': currency_ref.symbol,
                'position': currency_ref.position == 'after',
                'precision': currency_ref.decimal_places,
            },
            "total_paid_ref": currency_ref.round(values_data["total_paid_ref"]),
            "symbol_ref": currency_ref.symbol,
            "rate_today": rate_today,
            "products": values_data["products"],
            "payments": values_data["payments"],
            "taxes": values_data["taxes"],
        })
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
        sessions = self.env["pos.session"].browse(session_ids).exists() if session_ids else self.env["pos.session"]
        domain = [("state", "in", ["paid", "invoiced", "done"])]

        if session_ids:
            domain = AND([domain, [("session_id", "in", session_ids)]])
        else:
            user_tz = pytz.timezone(self.env.context.get("tz") or self.env.user.tz or "UTC")
            date_start_dt = fields.Datetime.to_datetime(date_start) if date_start else \
                            user_tz.localize(fields.Datetime.to_datetime(fields.Date.context_today(self))).astimezone(pytz.UTC)
            
            date_stop_dt = fields.Datetime.to_datetime(date_stop) if date_stop else \
                           date_start_dt + timedelta(days=1, seconds=-1)
            
            if date_stop_dt < date_start_dt:
                date_stop_dt = date_start_dt + timedelta(days=1, seconds=-1)

            domain = AND([domain, [
                ("date_order", ">=", fields.Datetime.to_string(date_start_dt)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop_dt)),
            ]])
            if config_ids:
                domain = AND([domain, [("config_id", "in", config_ids)]])

        orders = self.env["pos.order"].search(domain)
        total_ref = 0.0
        products_sold = defaultdict(float)
        taxes = {}

        for order in orders:
            total_ref += (order.amount_total_ref or 0.0)
            cur = order.currency_id

            for line in order.lines:
                # Incluimos price_unit_ref en la llave para agrupar correctamente
                key = (line.product_id, line.price_unit, getattr(line, 'price_unit_ref', 0.0), line.discount)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0),
                        cur, line.qty, product=line.product_id, partner=order.partner_id
                    )
                    for tax in line_taxes["taxes"]:
                        t_id = tax["id"]
                        taxes.setdefault(t_id, {
                            "name": tax["name"], "tax_amount": 0.0, "base_amount": 0.0,
                            "tax_amount_ref": 0.0, "base_amount_ref": 0.0,
                        })
                        taxes[t_id]["tax_amount"] += tax["amount"]
                        taxes[t_id]["base_amount"] += tax["base"]
                        if order.session_rate:
                            taxes[t_id]["tax_amount_ref"] += tax["amount"] / order.session_rate
                            taxes[t_id]["base_amount_ref"] += tax["base"] / order.session_rate
                else:
                    taxes.setdefault(0, {
                        "name": _("No Taxes"), "tax_amount": 0.0, "base_amount": 0.0,
                        "tax_amount_ref": 0.0, "base_amount_ref": 0.0,
                    })
                    taxes[0]["base_amount"] += line.price_subtotal_incl
                    taxes[0]["base_amount_ref"] += getattr(line, 'price_subtotal_incl_ref', 0.0)

        # Query de pagos mejorado para Odoo 17 (JSONB names)
        payments = []
        if orders:
            self.env.cr.execute("""
                SELECT
                    COALESCE(method.name->>%s, method.name->>'en_US') AS name,
                    SUM(payment.amount) AS total,
                    SUM(payment.amount_ref) AS total_ref
                FROM pos_payment payment
                JOIN pos_payment_method method ON payment.payment_method_id = method.id
                WHERE payment.pos_order_id IN %s
                GROUP BY method.id, name
                ORDER BY name
            """, (self.env.lang or 'en_US', tuple(orders.ids)))
            payments = self.env.cr.dictfetchall()

        products = sorted([{
            "product_id": p.id, "product_name": p.name, "code": p.default_code,
            "quantity": qty, "price_unit": pu, "price_unit_ref": pur,
            "discount": disc, "uom": p.uom_id.name,
        } for (p, pu, pur, disc), qty in products_sold.items()], key=lambda l: l["product_name"])

        return ({
            "total_paid_ref": total_ref,
            "taxes": list(taxes.values()),
            "payments": payments,
            "products": products,
        }, sessions)
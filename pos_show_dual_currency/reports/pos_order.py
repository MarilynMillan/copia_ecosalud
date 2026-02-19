# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from datetime import timedelta
from functools import partial
from itertools import groupby
from collections import defaultdict

import psycopg2
import pytz
import re

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero, float_round, float_repr, float_compare
from odoo.exceptions import ValidationError, UserError
from odoo.osv.expression import AND
import base64

_logger = logging.getLogger(__name__)


class ReportSaleDetails(models.AbstractModel):
    _inherit = 'report.point_of_sale.report_saledetails'

    @api.model
    def get_sale_details(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        # 1. Ejecutar el super original
        data = super(ReportSaleDetails, self).get_sale_details(date_start, date_stop, config_ids, session_ids)
        
        # 2. Buscar sesiones y datos personalizados
        pos_session = self.env['pos.session'].search([('id', 'in', session_ids)]) if session_ids else False
        values_data = self.update_key_values_data(date_start, date_stop, config_ids, session_ids)
        
        # 3. Determinar la tasa (Rate)
        rate_today = 1.0
        if pos_session:
            if pos_session[0].tax_today != 0:
                rate_today = pos_session[0].tax_today
        
        # 4. Manejo de productos (Priorizar datos de la sesión o de búsqueda manual)
        products = data.get('products', [])
        if not pos_session:
            products = values_data.get('products', [])

        # 5. Configurar moneda de referencia
        currency_id_dif = self.env.company.currency_id_dif
        data['currency_precision_ref'] = currency_id_dif.decimal_places
        data['symbol_ref'] = currency_id_dif.symbol
        data['symbol'] = self.env.company.currency_id.symbol
        data['rate_today'] = rate_today

        # --- CORRECCIÓN KEYERROR 'total_paid' ---
        # Si Odoo v17 no devuelve total_paid, lo calculamos de los pagos o usamos el total_ref
        total_original = data.get('total_paid', 0.0)
        
        if pos_session:
            # Si hay sesión, calculamos la referencia en base al total original
            data['total_paid_ref'] = currency_id_dif.round(total_original / rate_today) if rate_today else 0.0
        else:
            # Si es por rango de fechas, usamos el total ya calculado en update_key_values_data
            data['total_paid_ref'] = values_data.get('total_paid_ref', 0.0)

        # 6. Precios unitarios de referencia para productos
        for prod in products:
            if pos_session:
                # Evitar error si price_unit no viene en el diccionario
                p_unit = prod.get('price_unit', 0.0)
                prod['price_unit_ref'] = p_unit / rate_today if rate_today else 0.0
        
        # 7. Inyectar datos calculados manualmente al diccionario final
        data['products'] = products
        data['payments'] = values_data.get('payments', [])
        data['taxes'] = values_data.get('taxes', [])
        
        return data

    def update_key_values_data(self, date_start=False, date_stop=False, config_ids=False, session_ids=False):
        domain = [('state', 'in', ['paid', 'invoiced', 'done'])]
        
        if session_ids:
            domain = AND([domain, [('session_id', 'in', session_ids)]])
        else:
            # Lógica de fechas estándar de Odoo
            if date_start:
                date_start = fields.Datetime.to_datetime(date_start)
            else:
                user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
                today = user_tz.localize(fields.Datetime.to_datetime(fields.Date.context_today(self)))
                date_start = today.astimezone(pytz.timezone('UTC'))

            if date_stop:
                date_stop = fields.Datetime.to_datetime(date_stop)
                if date_stop < date_start:
                    date_stop = date_start + timedelta(days=1, seconds=-1)
            else:
                date_stop = date_start + timedelta(days=1, seconds=-1)

            domain = AND([domain, [
                ('date_order', '>=', fields.Datetime.to_string(date_start)),
                ('date_order', '<=', fields.Datetime.to_string(date_stop))
            ]])

            if config_ids:
                domain = AND([domain, [('config_id', 'in', config_ids)]])

        orders = self.env['pos.order'].search(domain)
        user_currency = self.env.company.currency_id
        total_ref = 0.0
        products_sold = {}
        taxes = {}

        for order in orders:
            total_ref += order.amount_total_ref
            currency = order.session_id.currency_id

            for line in order.lines:
                key = (line.product_id, line.price_unit, line.price_unit_ref, line.discount)
                products_sold.setdefault(key, 0.0)
                products_sold[key] += line.qty

                if line.tax_ids_after_fiscal_position:
                    line_taxes = line.tax_ids_after_fiscal_position.sudo().compute_all(
                        line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency, line.qty,
                        product=line.product_id, partner=line.order_id.partner_id or False)
                    
                    for tax in line_taxes['taxes']:
                        taxes.setdefault(tax['id'], {
                            'name': tax['name'], 'tax_amount': 0.0, 'base_amount': 0.0,
                            'tax_amount_ref': 0.0, 'base_amount_ref': 0.0
                        })
                        taxes[tax['id']]['tax_amount'] += tax['amount']
                        taxes[tax['id']]['base_amount'] += tax['base']
                        
                        if order.session_rate != 0:
                            taxes[tax['id']]['tax_amount_ref'] += tax['amount'] / order.session_rate
                            taxes[tax['id']]['base_amount_ref'] += tax['base'] / order.session_rate
                else:
                    taxes.setdefault(0, {
                        'name': _('No Taxes'), 'tax_amount': 0.0, 'base_amount': 0.0,
                        'tax_amount_ref': 0.0, 'base_amount_ref': 0.0
                    })
                    taxes[0]['base_amount'] += line.price_subtotal_incl
                    taxes[0]['base_amount_ref'] += line.price_subtotal_incl_ref

        # Cálculo de pagos con SQL para velocidad
        payment_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
        payments = []
        if payment_ids:
            # En Odoo 17 el campo name en pos_payment_method es un JSON (traducible)
            self.env.cr.execute("""
                SELECT COALESCE(method.name->>%s, method.name->>'en_US') as name, 
                       sum(amount) total, sum(amount_ref) total_ref
                FROM pos_payment AS payment,
                     pos_payment_method AS method
                WHERE payment.payment_method_id = method.id
                  AND payment.id IN %s
                GROUP BY method.name
            """, (self.env.lang or 'en_US', tuple(payment_ids),))
            payments = self.env.cr.dictfetchall()

        return {
            'total_paid_ref': self.env.company.currency_id_dif.round(total_ref),
            'taxes': list(taxes.values()),
            'payments': payments,
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'price_unit_ref': price_unit_ref,
                'discount': discount,
                'uom': product.uom_id.name,
            } for (product, price_unit, price_unit_ref, discount), qty in products_sold.items()],
                key=lambda l: l['product_name'])
        }

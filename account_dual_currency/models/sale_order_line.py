# -*- coding: utf-8 -*-

from itertools import groupby
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    def _prepare_invoice_line(self, **optional_values):
        """Prepare the values to create the new invoice line for a sales order line.

        :param optional_values: any parameter that should be added to the returned invoice line
        :rtype: dict
        """
        tax_today = self.company_id.currency_id_dif.inverse_company_rate
        self.ensure_one()
        res = {
            'display_type': self.display_type or 'product',
            'sequence': self.sequence,
            'name': self.name,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom.id,
            'quantity': self.qty_to_invoice,
            'discount': self.discount,
            'price_unit': self.price_unit if self.currency_id == self.company_id.currency_id else self.price_unit * tax_today,
            'price_unit_usd': self.price_unit if self.currency_id == self.company_id.currency_id_dif else self.price_unit / tax_today,
            'price_subtotal_usd': self.price_subtotal if self.currency_id == self.company_id.currency_id_dif else self.price_subtotal / tax_today,
            'tax_ids': [Command.set(self.tax_id.ids)],
            'sale_line_ids': [Command.link(self.id)],
            'is_downpayment': self.is_downpayment,
        }
        self._set_analytic_distribution(res, **optional_values)
        if optional_values:
            res.update(optional_values)
        if self.display_type:
            res['account_id'] = False
        return res
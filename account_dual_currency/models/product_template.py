# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class Productos(models.Model):
    _inherit = 'product.template'

    currency_id_dif = fields.Many2one('res.currency', string='Moneda Diferente', default=lambda self: self.env.company.currency_id_dif.id)

    list_price_usd = fields.Float(string="Precio de venta $", currency_field='currency_id_dif', inverse='_set_list_price_usd', compute='_compute_list_price_usd', digits='Product_Price_USD')
    standard_price_usd = fields.Float(string="Costo $", inverse='_set_standard_price_usd', compute='_compute_standard_price_usd', currency_field='currency_id_dif')
    last_cost_usd = fields.Float(string="Ultimo costo $", inverse='_set_last_cost_usd', compute='_compute_last_cost_usd')


    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.list_price_usd')
    def _compute_list_price_usd(self):
        # Depends on force_company context because list_price_usd is company_dependent
        # on the product_product
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.list_price_usd = template.product_variant_ids.list_price_usd
        for template in (self - unique_variants):
            template.list_price_usd = 0.0

    def _set_list_price_usd(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.list_price_usd = template.list_price_usd

    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.last_cost_usd')
    def _compute_last_cost_usd(self):
        # Depends on force_company context because last_cost_usd is company_dependent
        # on the product_product
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.last_cost_usd = template.product_variant_ids.last_cost_usd
        for template in (self - unique_variants):
            template.last_cost_usd = 0.0

    def _set_last_cost_usd(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.last_cost_usd = template.last_cost_usd

    def _set_standard_price_usd(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.standard_price_usd = template.standard_price_usd

    @api.depends_context('company')
    @api.depends('product_variant_ids', 'product_variant_ids.standard_price_usd')
    def _compute_standard_price_usd(self):
        # Depends on force_company context because standard_price is company_dependent
        # on the product_product
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.standard_price_usd = template.product_variant_ids.standard_price_usd
        for template in (self - unique_variants):
            template.standard_price_usd = 0.0

    @api.onchange('list_price_usd')
    def _onchange_list_price_usd(self):
        for rec in self:
            if rec.list_price_usd:
                if rec.list_price_usd >0:
                    tasa = self.env.company.currency_id_dif
                    if tasa:
                        rec.list_price = rec.list_price_usd * (tasa.inverse_company_rate)

    @api.onchange('standard_price_usd')
    def _onchange_standard_price_usd(self):
        for rec in self:
            if len(rec.product_variant_ids) == 1:
                rec.product_variant_ids[0].standard_price_usd = rec.standard_price_usd

            if rec.standard_price_usd and rec.categ_id.property_valuation == 'manual_periodic':
                if rec.standard_price_usd > 0:
                    tasa = self.env.company.currency_id_dif
                    if tasa:
                        rec.standard_price = rec.standard_price_usd * (tasa.inverse_company_rate)



# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config_id):
        models = super()._load_pos_data_models(config_id)
        payment_method_model = next((m for m in models if m['model'] == 'pos.payment.method'), None)
        if payment_method_model:
            payment_method_model['fields'].extend(['x_igtf_percentage', 'x_is_foreign_exchange'])
        return models

class PosOrder(models.Model):
    _inherit = "pos.order"

    x_igtf_amount = fields.Monetary("Monto IGTF", compute="_compute_x_igtf_amount", store=True)

    @api.depends("lines.x_is_igtf_line", "lines.price_subtotal_incl")
    def _compute_x_igtf_amount(self):
        for rec in self:
            rec.x_igtf_amount = sum(rec.lines.filtered("x_is_igtf_line").mapped("price_subtotal_incl"))

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        # Asegurar que procesamos campos extra si vienen en la orden
        return order_fields
        
class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    x_is_igtf_line = fields.Boolean("Linea IGTF")


    def _export_for_ui(self, orderline):
        res = super()._export_for_ui(orderline)

        res["x_is_igtf_line"] = orderline.x_is_igtf_line

        return res

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    x_igtf_percentage = fields.Float("Porcentaje de IGTF")
    x_is_foreign_exchange = fields.Boolean("Pago en divisas")

    @api.constrains("x_igtf_percentage")
    def _check_x_igtf_percentage(self):
        for rec in self:
            if rec.x_igtf_percentage < 0 and rec.x_is_foreign_exchange:
                raise ValidationError("El porcentage IGTF debe ser mayor a cero")

class PosConfig(models.Model):
    _inherit = "pos.config"

    x_igtf_product_id = fields.Many2one("product.product", "Producto IGTF", tracking=True)

    aplicar_igtf = fields.Boolean("Aplicar IGTF", default=False)

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_x_igtf_product_id = fields.Many2one(
        string="Producto IGTF", 
        related="pos_config_id.x_igtf_product_id",
        readonly=False,
        store=True,
    )

    aplicar_igtf = fields.Boolean(related="pos_config_id.aplicar_igtf", readonly=False, store=True)

    @api.constrains("pos_x_igtf_product_id")
    def _check_pos_x_igtf_product_id(self):
        for rec in self.filtered("pos_x_igtf_product_id"):
            if sum(rec.pos_x_igtf_product_id.taxes_id.mapped("amount")) != 0:
                raise ValidationError("El producto IGTF debe ser exento")






from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
class PosConfig(models.Model):
    _inherit = "pos.config"


    show_dual_currency = fields.Boolean(
        string="Show Other Currency in POS", 
        help="Muestra una segunda moneda en el POS (ej. USD en Venezuela)", 
        default=True
    )

    # CORRECCIÓN: Cambiamos 'Rate' por 'Tasa Compañía' para evitar duplicados
    rate_company = fields.Float(
        string='Rate Compañy', 
        related='currency_id.rate', 
        digits=(12, 6) # Es mejor definir dígitos para tasas
    )

    show_currency = fields.Many2one(
        'res.currency', 
        string='Moneda Secundaria', 
        default=lambda self: self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
    )

    # CORRECCIÓN: Cambiamos 'Rate' por 'Tasa Dual'
    show_currency_rate = fields.Float(
        string='Rate Dual', 
        related='show_currency.rate',
        digits=(12, 6)
    )

    show_currency_symbol = fields.Char(
        string="Simbol Rate Dual",
        related='show_currency.symbol'
    )

    # CORRECCIÓN: En v17, no es necesario re-definir la lista de selección en un related
    show_currency_position = fields.Selection(
        related='show_currency.position',
        string="Position Ssimbol Dual"
    )

    default_location_src_id = fields.Many2one(
        "stock.location", 
        related="picking_type_id.default_location_src_id",
        string="Ubication the Origen"
    )

    @api.constrains('pricelist_id', 'use_pricelist', 'available_pricelist_ids', 'invoice_journal_id')
    def _check_currencies_dual(self):
        for config in self:
            # Validación de listas de precios (estándar v17)
            if config.use_pricelist and config.pricelist_id not in config.available_pricelist_ids:
                raise ValidationError(_("La lista de precios por defecto debe estar incluida en las disponibles."))

            # Validación de moneda de listas de precios
            if any(config.available_pricelist_ids.mapped(lambda pl: pl.currency_id != config.currency_id)):
                raise ValidationError(_("Todas las listas de precios disponibles deben estar en la misma moneda que el POS."))

            # Validación de diario de facturación
            if config.invoice_journal_id.currency_id and config.invoice_journal_id.currency_id != config.currency_id:
                raise ValidationError(_("El diario de factura debe estar en la misma moneda que el Punto de Venta."))
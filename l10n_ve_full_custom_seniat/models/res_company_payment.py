from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    # Campo para texto enriquecido (Bancos, Pago Movil)
    payment_info_fiscal = fields.Html(string="Información de Pagos (PDF)")
    # Campo para la imagen QR
    payment_qr_fiscal = fields.Binary(string="Código QR de Pago")

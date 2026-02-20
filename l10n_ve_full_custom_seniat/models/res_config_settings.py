# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_info_fiscal = fields.Html(related='company_id.payment_info_fiscal', readonly=False)
    payment_qr_fiscal = fields.Binary(related='company_id.payment_qr_fiscal', readonly=False)

# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.http import request, content_disposition
from datetime import datetime
import random
import re

import logging

_logger = logging.getLogger(__name__)


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    file_name = fields.Char(string='name file')
    file_txt = fields.Binary(string='Archivo txt')

    def generate_file_txt(self):
        self.ensure_one()
        # if not self.journal_id.name_file_txt:
        #     raise UserError(_("El diario no tiene configurado un nombre de archivo txt."))
        if not self.journal_id.bank_account_id:
            raise UserError(_("El diario no tiene configurada una cuenta bancaria."))

        # Capturamos el nombre del archivo guardado en el modelo de diarios (journal)
        cstm_bank_file_name = self.journal_id.name_file_txt
        #self.file_name = cstm_bank_file_name + '.txt'

        # Capturamos el banco asociado y ejecutamos la función para generar el txt según el banco.
        prex_bank = str(self.journal_id.bank_account_id.acc_number)[0:4]
        fn_bank = getattr(self, 'bank_%s' % prex_bank, None)
        content = ""
        filename = ""
        if fn_bank:
            content, filename = fn_bank()
        else:
            raise UserError(_("No se ha implementado la generación de archivo txt para el banco asociado."))

        # Genera el contenido del archivo TXT y lo guardamos en base de datos.
        self.file_txt = base64.b64encode(content.encode())
        self.file_name = filename
        message = "Archivo txt generado correctamente: %s" % (filename)
        self.message_post(body=message)

        # Descarga automatica.
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        attachment_obj = self.env['ir.attachment']
        attachment_id = attachment_obj.create({'name': filename, 'mimetype': 'text/plain', 'datas': self.file_txt})
        download_url = '/web/content/' + str(attachment_id.id) + '?download=true'
        return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
        }

    # Venezuela.
    def bank_0102(self):
        return "Ejemplo banco de Venezuela"

    # Banesco.
    def bank_0134(self):

        return "Ejemplo banco BANESCO"

    # Mercantil.
    def bank_0105(self):
        return "Ejemplo banco Mercantil"

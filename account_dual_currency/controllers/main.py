# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import Response, request
import logging

_logger = logging.getLogger(__name__)


class Main(http.Controller):
    @http.route("/currency/get_rate", auth="public", type="json", method=["POST"], csrf=False)
    def get_rate(self, **kwargs):
        data = request.get_json_data()
        IrConfigParam = request.env["ir.config_parameter"].sudo() 
        verification_token = IrConfigParam.get_param("api_rate", "")

        #verificar token como Autorizacion Bearer la cabecera 
        if not request.httprequest.headers.get("Authorization"): 
            return {"status": "400", "message": "Invalid token"}
        if not request.httprequest.headers.get("Authorization").replace("Bearer ", "") == verification_token:
            return {"status": "400", "message": "Invalid token"}

        # Validamos la moneda.
        if not data.get("currency"):
            return {"status": "400", "message": "Request error: Currency not obtained"}
        if data.get("currency").upper() not in ("USD", "EUR"):
            return {"status": "400", "message": "Request error: The currency is not on the allowed list"}

        # Consultamos los datos de la moneda.
        res_currency = request.env["res.currency"].sudo()
        currency = res_currency.search_read([("name","=",data.get("currency"))], limit=1)
        # Consultamos la ultima actualización de la tasa.
        res_currency_rate = request.env["res.currency.rate"].sudo()
        data = res_currency_rate.search([("currency_id","=",currency[0]["id"])], order="name desc", limit=1)
        return {
            "status": "200",
            "message": {
                "date": data[0]["name"],
                "rate": data[0]["inverse_company_rate"],
            },
        }

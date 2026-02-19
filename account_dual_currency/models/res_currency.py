from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
import requests
import urllib3
import math
urllib3.disable_warnings()
import logging
_logger = logging.getLogger(__name__)

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    facturas_por_actualizar = fields.Boolean(compute="_facturas_por_actualizar")

    # habilitar sincronización automatica
    sincronizar = fields.Boolean(string="Sincronizar", default=False)

    # campo listado de servidores, bcv o dolar today
    server = fields.Selection([('bcv', 'BCV')], string='Servidor',
                              default='bcv')

    act_productos = fields.Boolean(string="Actualizar Productos", default=False)

    inverse_company_rate = fields.Float('Tasa de la compañía', compute='_compute_inverse_company_rate')

    def _truncate_fiscal(self, amount, decimal_places=None):
        """Truncamiento fiscal para Venezuela (no redondeo)"""
        if decimal_places is None:
            decimal_places = self.decimal_places
        factor = 10 ** decimal_places
        return math.floor(amount * factor) / factor

    def round(self, amount):
        """Sobrescribir round para VES con truncamiento fiscal"""
        if self.name == 'VES':
            return self._truncate_fiscal(amount)
        return super().round(amount)

    def _compute_inverse_company_rate(self):
        #toma el ultimo registro de la tasa de cambio en res.currency.rate
        for rec in self:
            company_id = self.env.company
            rates = company_id.currency_id_dif._get_rates(company_id, date.today())
            rates = 1 / rates[company_id.currency_id_dif.id] if rates else 1
            decimal_dual_currency_rate = self.env['decimal.precision'].precision_get('Dual_Currency_rate')
            if rates:
                rec.inverse_company_rate = rates  # Guardar tasa completa sin redondear
            else:
                rec.inverse_company_rate = 0

    def _convert(self, from_amount, to_currency, company=None, date=None, round=True):
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            if self.env.context.get('tasa_factura'):
                if to_currency == self.env.company.currency_id_dif:
                    to_amount = from_amount / self.env.context.get('tasa_factura')
                else:
                    to_amount = from_amount * self.env.context.get('tasa_factura')
            else:
                if from_amount:
                    to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
                else:
                    return  0.0
        # apply rounding - MODIFICADO PARA VENEZUELA
        if round:
            # Para VES, usar truncamiento fiscal
            if to_currency.name == 'VES':
                return to_currency._truncate_fiscal(to_amount)
            else:
                return to_currency.round(to_amount)
        else:
            return to_amount

    def _facturas_por_actualizar(self):
        for rec in self:
            if rec.name == self.env.company.currency_id_dif.name:
                if self.env['account.move'].search_count([('state', 'in', ['draft','posted'])]):
                    rec.facturas_por_actualizar = True
                else:
                    rec.facturas_por_actualizar = False
            else:
                rec.facturas_por_actualizar = False


    def actualizar_facturas(self):
        for rec in self:
            # actualizar tasa a las facturas dinamicas
            facturas = self.env['account.move'].search([('acuerdo_moneda', '=', True)])
            if facturas:
                for f in facturas:
                    f.tax_today = rec.inverse_company_rate
                    for l in f.line_ids:
                        l.tax_today = rec.inverse_company_rate
                        l._debit_usd()
                        l._credit_usd()
                    for d in f.invoice_line_ids:
                        d.tax_today = rec.inverse_company_rate
                        d._price_unit_usd()
                        d._price_subtotal_usd()
                    #f._amount_untaxed_usd()
                    f._amount_all_usd()
                    f._compute_payments_widget_reconciled_info_USD()

    def actualizar_productos(self):
        for rec in self:
            company_ids = self.env['res.company'].sudo().search([('parent_id', '=', False)])
            product_ids = self.env['product.template'].search([('list_price_usd','>',0)])
            for p in product_ids:
                for c in company_ids:
                    p.with_company(c.id).list_price = p.with_company(c.id).list_price_usd * (rec.inverse_company_rate)

            product_product_ids = self.env['product.product'].search([('list_price_usd', '>', 0)])
            for p in product_product_ids:
                for c in company_ids:
                    p.with_company(c.id).list_price = p.with_company(c.id).list_price_usd * (rec.inverse_company_rate)

            list_product_ids = self.env['product.pricelist.item'].search([('currency_id', '=', self.id)])

            for lp in list_product_ids:
                # buscar el producto en la lista de Bs y actualizar
                dominio = [('currency_id', '=', lp.company_id.currency_id.id or self.env.company.currency_id.id)]
                if lp.product_id:
                    dominio.append((('product_id', '=', lp.product_id.id)))
                elif lp.product_tmpl_id:
                    dominio.append((('product_tmpl_id', '=', lp.product_tmpl_id.id)))
                product_id_bs = self.env['product.pricelist.item'].search(dominio)
                for p in product_id_bs:
                    p.fixed_price = lp.fixed_price * (rec.inverse_company_rate)

            channel_id = self.env.ref('account_dual_currency.trm_channel')
            channel_id.message_post(
                body="Todos los productos han sido actualizados con la nueva tasa de cambio",
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

    # --- FUNCION get_bcv (Devuelve un estado) ---
    def get_bcv(self):
        try:
            url = "https://www.bcv.org.ve/"
            req = requests.get(url, verify=False, timeout=10)
        except requests.exceptions.RequestException as e:
            _logger.warning(f"Fallo al conectar con BCV: {e}")
            return {'status': 'fail_connection'}

        if req.status_code != 200:
            return {'status': 'fail_connection'}

        try:
            html = BeautifulSoup(req.text, "html.parser")
            dolar_div = html.find('div', {'id': 'dolar'})
            dolar_strong = dolar_div.find('strong')
            dolar_text = str(dolar_strong).split()
            dolar_clean = str.replace(dolar_text[1], '.', '')
            dolar = float(str.replace(dolar_clean, ',', '.'))

            euro_div = html.find('div', {'id': 'euro'})
            euro_strong = euro_div.find('strong')
            euro_text = str(euro_strong).split()
            euro_clean = str.replace(euro_text[1], '.', '')
            euro = float(str.replace(euro_clean, ',', '.'))

            fecha_valor = html.find('span', {'class': 'date-display-single'})
            attrs_content = fecha_valor.attrs['content']
            fecha_bcv = datetime.strptime(attrs_content, '%Y-%m-%dT%H:%M:%S%z').date()

        except Exception as e:
            _logger.warning(f"Fallo en el scraping de BCV (Pagina cambio?): {e}")
            # Esto atrapa el 'NoneType' object has no attribute 'find'
            return {'status': 'fail_scraping'}

        # --- Logica de Fin de Semana ---
        if fecha_bcv < date.today():
             return {'status': 'fail_date_old'}

        rate_to_return = False
        if self.name == 'USD':
            rate_to_return = dolar
        elif self.name == 'EUR':
            rate_to_return = euro

        if rate_to_return:
            return {'status': 'success', 'rate': rate_to_return}
        else:
            return {'status': 'fail_scraping'} # Moneda no es USD o EUR

    # --- FUNCION actualizar_tasa (Muestra POP-UPs) ---
    def actualizar_tasa(self):
        for rec in self:
            nueva_tasa = 0
            if rec.server == 'bcv':
                bcv_data = rec.get_bcv() # Obtenemos el diccionario de estado

                # --- Manejador de Error 1: BCV Caido o Pagina Cambiada ---
                if bcv_data['status'] == 'fail_connection' or bcv_data['status'] == 'fail_scraping':
                    raise UserError(
                        "No se pudo obtener la tasa del BCV.\n\n"
                        "Verifique si la plataforma del Banco Central de Venezuela (bcv.org.ve) está disponible "
                        "o si su diseño ha cambiado."
                    )

                # --- Manejador de Error 2: Tasa de Fin de Semana ---
                if bcv_data['status'] == 'fail_date_old':
                    raise UserError(
                        "La tasa del BCV no ha sido actualizada (es fin de semana).\n\n"
                        "La tasa publicada sigue siendo la del último día hábil. "
                        "Intente de nuevo el próximo día hábil."
                    )

                # --- Caso de Exito ---
                if bcv_data['status'] == 'success':
                    nueva_tasa = bcv_data['rate']

            if nueva_tasa > 0:
                decimal_dual_currency_rate = self.env['decimal.precision'].precision_get('Dual_Currency_rate')
                nueva_tasa = round(nueva_tasa, decimal_dual_currency_rate if decimal_dual_currency_rate else 2)
                channel_id = self.env.ref('account_dual_currency.trm_channel')
                company_ids = self.env['res.company'].sudo().search([('parent_id', '=', False)])
                nueva = True
                for c in company_ids:
                    tasa_actual = self.env['res.currency.rate'].sudo().search(
                        [('name', '=', datetime.now()), ('currency_id', '=', self.id), ('company_id', '=', c.id)])
                    if len(tasa_actual) == 0:
                        self.env['res.currency.rate'].sudo().create({
                            'currency_id': self.id,
                            'name': datetime.now(),
                            'rate': 1/nueva_tasa,
                            'company_id': c.id,
                        })

                    else:
                        if rec.server== 'dolar_today':
                            tasa_actual.rate = nueva_tasa
                        nueva = False

                if nueva:
                    channel_id.message_post(
                        body="Nueva tasa de cambio del %s: %s, actualizada desde %s a las %s." % (
                            rec.name, nueva_tasa, rec.server,
                            datetime.strftime(fields.Datetime.context_timestamp(self, datetime.now()),
                                              "%d-%m-%Y %H:%M:%S")),
                        message_type='notification',
                        subtype_xmlid='mail.mt_comment',
                    )
                    if rec.act_productos:
                        rec.actualizar_productos()
                else:
                    pass

    # --- FUNCION DEL CRON (AHORA ENVIA MENSAJES DE ERROR AL CHAT) ---
    @api.model
    def _cron_actualizar_tasa(self):
        channel_id = self.env.ref('account_dual_currency.trm_channel', raise_if_not_found=False)
        monedas = self.env['res.currency'].search([('active', '=', True), ('sincronizar', '=',True)])

        for m in monedas:
            try:
                # Intenta actualizar. Si tiene exito, la funcion interna envia el chat de "Nueva tasa..."
                m.actualizar_tasa()

            except UserError as e:
                # ¡Atrapamos el error de "Fin de Semana" o "BCV Caido"!
                # El cron no debe fallar, solo debe notificar.
                _logger.warning(f"Cron de tasa: {e.args[0]}") # Log del servidor

                # Publicamos el error en el chat
                if channel_id:
                    mensaje_chat = (
                        f"⚠️ **ALERTA DE TASA ({m.name}):**\n\n"
                        f"{e.args[0]}\n\n"
                        "El administrador debe verificar el servicio o aplicar la tasa manualmente."
                    )
                    channel_id.message_post(
                        body=mensaje_chat,
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )

            except Exception as e:
                # Otro error inesperado (ej. programacion)
                _logger.error(f"Fallo inesperado en el Cron de actualizar tasa: {e}")
                if channel_id:
                    channel_id.message_post(
                        body=f"❌ **ERROR CRITICO DE TASA ({m.name}):**\n\n{e}",
                        message_type='comment',
                        subtype_xmlid='mail.mt_comment',
                    )

    # --- FUNCION DEL WIDGET UNICO (SIN CAMBIOS) ---
    def get_bcv_systray_rates(self):
        company_id = self.env.company
        result = {'usd_rate': 0, 'eur_rate': 0}

        # --- Get USD Rate (logic from old get_trm_systray) ---
        try:
            usd_rates_data = company_id.currency_id_dif._get_rates(company_id, date.today())
            usd_rate = 1 / usd_rates_data[company_id.currency_id_dif.id]
            result['usd_rate'] = '{:,.4f}'.format(usd_rate)
        except Exception:
            result['usd_rate'] = 0.0 # Failed to get USD

        # --- Get EUR Rate (logic from old get_eur_systray) ---
        try:
            eur_currency = self.env['res.currency'].search([('name', '=', 'EUR')], limit=1)
            if eur_currency:
                eur_rates_data = eur_currency._get_rates(company_id, date.today())
                if eur_rates_data and eur_currency.id in eur_rates_data:
                    eur_rate = 1 / eur_rates_data[eur_currency.id]
                    result['eur_rate'] = '{:,.4f}'.format(eur_rate)
        except Exception:
            result['eur_rate'] = 0.0 # Failed to get EUR

        return result

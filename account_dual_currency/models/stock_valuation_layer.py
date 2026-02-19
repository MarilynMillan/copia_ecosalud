# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import ValidationError
import datetime

class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    currency_id_dif = fields.Many2one("res.currency",
                                     string="Divisa de Referencia",
                                     default=lambda self: self.env.company.currency_id_dif )
    unit_cost_usd = fields.Monetary('Valor unitario $', readonly=True, default=0,currency_field='currency_id_dif')
    value_usd = fields.Monetary('Valor Total $', readonly=True, default=0,currency_field='currency_id_dif')
    remaining_value_usd = fields.Monetary('Valor Restante $', readonly=True, default=0,currency_field='currency_id_dif')
    tasa = fields.Float('Tasa de Referencia', readonly=True, force_save=True, digits='Dual_Currency_rate')

    def write(self, vals):

        company = self.company_id
        if not 'unit_cost_usd' in vals and not 'value_usd' in vals:
            if not 'quantity' in vals and self.stock_move_id:
                new_rate = company.currency_id_dif.inverse_company_rate
                for rec in self:
                    if rec.stock_move_id:
                        picking_id = rec.stock_move_id.picking_id
                        date = datetime.date.today()
                        if picking_id:
                            date = picking_id.date_of_transfer or picking_id.create_date
                        new_rate_ids = company.currency_id_dif._get_rates(company, date)
                        if new_rate_ids:
                            new_rate = 1 / new_rate_ids[company.currency_id_dif.id]
                if 'unit_cost' in vals:

                    standard_price_usd = float(vals['unit_cost']) / new_rate
                    vals['unit_cost_usd'] = standard_price_usd
                    if vals.get('stock_move_id') or self.stock_move_id:
                        stock_move_id = self.env['stock.move'].search(
                            [('id', '=', vals.get('stock_move_id') or self.stock_move_id.id)])
                        if stock_move_id.location_id.usage == 'supplier':
                            self.product_id.with_company(company.id).standard_price_usd = standard_price_usd
                if 'value' in vals:
                    value_usd = float(vals['value']) / new_rate
                    vals['value_usd'] = value_usd
        if 'account_move_id' in vals:
            new_rate = company.currency_id_dif.inverse_company_rate
            product_id = self.product_id
            for rec in self:
                if rec.stock_move_id:
                        picking_id = rec.stock_move_id.picking_id
                        date = datetime.date.today()
                        if picking_id:
                            date = picking_id.date_of_transfer or picking_id.create_date
                        new_rate_ids = company.currency_id_dif._get_rates(company,date)
                        if new_rate_ids:
                            new_rate = 1 / new_rate_ids[company.currency_id_dif.id]
                move_id = self.env['account.move'].sudo().with_context(check_move_validity=False).search(
                    [('id', '=', vals['account_move_id'])])

                if move_id:
                    move_id.line_ids.no_calcular = True
                    #move_id.button_draft()
                    ##print('move_id.line_ids[0].currency_id',move_id.line_ids[0].currency_id)
                    ##print('rec.currency_id',rec.currency_id)
                    if move_id.line_ids[0].currency_id != rec.currency_id:
                        for l in move_id.line_ids:
                            l.currency_id = rec.currency_id
                            if rec.value > 0:
                                if l.amount_currency < 0:
                                    l.amount_currency = rec.value * -1
                                else:
                                    l.amount_currency = rec.value
                            if rec.value < 0:
                                if l.amount_currency > 0:
                                    l.amount_currency = rec.value * -1
                                else:
                                    l.amount_currency = rec.value


                    if rec.stock_move_id.location_id.usage == 'supplier':
                        move_id.tax_today = new_rate
                    else:
                        move_id.tax_today = rec.tasa

                    for l in move_id.line_ids:
                        if l.credit > 0:
                            l.credit_usd = abs(rec.value_usd)
                        if l.debit > 0:
                            l.debit_usd = abs(rec.value_usd)

                    # if move_id.state == 'draft':
                    #     move_id._post()
        res = super(StockValuationLayer, self).write(vals)
        for rec in self:
            if rec.account_move_id:
                ##print('rec.value_usd', rec.value_usd)
                for l in rec.account_move_id.line_ids:
                    if l.credit > 0:
                        l.credit_usd = abs(rec.value_usd)
                    if l.debit > 0:
                        l.debit_usd = abs(rec.value_usd)
                    ##print('l.debit_usd', l.debit_usd)
                    ##print('l.credit_usd', l.credit_usd)
        return res

    def create(self, vals):
        if isinstance(vals, list):
            for val in vals:
                company = self.env['res.company'].browse(val.get('company_id') or self.env.company.id)
                if 'stock_move_id' in val:
                    stock_move_id = self.env['stock.move'].search([('id', '=', val['stock_move_id'])])
                    if company.return_actual_cost:
                        #verificar si el tipo de operacion es de entrada y si posee en el picking_id el grupo se aprovisiona y si tiene dentro de ese grupo una orden de venta
                        if stock_move_id.picking_id.picking_type_id.code == 'incoming' and stock_move_id.picking_id.group_id and stock_move_id.picking_id.group_id.sale_id:
                            #reeemplazar los valores de value, unit_cost, remaining_value
                            product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                            if product_id.with_company(company.id).cost_method in ('average', 'fifo'):
                                val['value'] = product_id.with_company(company.id).standard_price * float(val['quantity'])
                                val['unit_cost'] = product_id.with_company(company.id).standard_price
                                val['remaining_value'] = product_id.with_company(company.id).standard_price * float(val['quantity'])
                                #reemplaza tambien los valores en dolares
                                val['value_usd'] = product_id.with_company(company.id).standard_price_usd * float(val['quantity'])
                                val['unit_cost_usd'] = product_id.with_company(company.id).standard_price_usd
                                val['remaining_value_usd'] = product_id.with_company(company.id).standard_price_usd * float(val['quantity'])
                                if val['unit_cost'] == 0 or val['unit_cost_usd'] == 0:
                                    raise ValidationError(_("The cost and dollar cost of the product cannot be 0"))
                                new_rate = val['unit_cost'] / val['unit_cost_usd']
                                val['tasa'] = new_rate
                    if not 'unit_cost_usd' in val:
                        #verificar si el tipo de operacion es de entrada y es una ubicacion de perdida de inventario
                        if stock_move_id.location_id.usage == 'inventory' and float(val['quantity']) > 0:
                                #reeemplazar los valores de value, unit_cost, remaining_value
                                product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                                if product_id.with_company(company.id).cost_method in ('average', 'fifo'):
                                    #reemplaza los valores en dolares
                                    valor_usd = product_id.with_company(company.id).standard_price_usd * float(val['quantity'])
                                    if abs(valor_usd) > abs(val['value']):
                                        #busca la tasa actual
                                        val['value_usd'] = val['value'] / company.currency_id_dif.inverse_company_rate
                                    else:
                                        val['value_usd'] = product_id.with_company(company.id).standard_price_usd * float(val['quantity'])
                                    unit_cost_usd = val['value_usd'] / float(val['quantity'])
                                    val['unit_cost_usd'] = unit_cost_usd
                                    val['remaining_value_usd'] = unit_cost_usd * float(val['quantity'])
                                    if val['unit_cost'] == 0 or val['unit_cost_usd'] == 0:
                                        raise ValidationError(_("The cost and dollar cost of the product cannot be 0"))
                                    new_rate = val['unit_cost'] / val['unit_cost_usd']
                                    val['tasa'] = new_rate

                if not 'unit_cost_usd' in val and not 'value_usd' in val:
                    if val.get('quantity'):
                        if float(val['quantity']) != 0:
                            supplier = False
                            product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                            standard_price_usd = 0
                            new_rate = company.currency_id_dif.inverse_company_rate
                            if 'stock_move_id' in val:
                                stock_move_id = self.env['stock.move'].search([('id', '=', val['stock_move_id'])])
                                if stock_move_id:
                                    picking_id = stock_move_id.picking_id
                                    date = datetime.date.today()
                                    if picking_id:
                                        date = picking_id.date_of_transfer or picking_id.create_date
                                    new_rate_ids = company.currency_id_dif._get_rates(company,date)
                                    if new_rate_ids:
                                        new_rate = 1 / new_rate_ids[company.currency_id_dif.id]
                                if stock_move_id.location_id.usage in ['supplier','production']:
                                    supplier = True
                                else:
                                    if 'tasa' in val:
                                        new_rate = val['tasa']

                            if 'stock_move_id' in val:
                                standard_price_usd = float(val['unit_cost']) / new_rate
                            else:
                                standard_price_usd = product_id.with_company(company.id).standard_price_usd
                                if abs(standard_price_usd) > abs(product_id.with_company(company.id).standard_price):
                                    standard_price_usd = product_id.with_company(company.id).standard_price / company.currency_id_dif.inverse_company_rate
                                    product_id.with_company(company.id).standard_price_usd = standard_price_usd
                            if val['value'] < 0 and standard_price_usd > 0:
                                standard_price_usd  = standard_price_usd *-1

                            val['unit_cost_usd'] = round(standard_price_usd,company.currency_id_dif.decimal_places)
                            val['value_usd'] = float(val['quantity']) * val['unit_cost_usd']
                            val['tasa'] = new_rate
                            if product_id.with_company(company.id).cost_method in ('average', 'fifo') and supplier:
                                val['remaining_value_usd'] = float(val['quantity']) * standard_price_usd
                            if 'stock_move_id' in val:
                                stock_move_id = self.env['stock.move'].search([('id', '=', val.get('stock_move_id'))])
                                if stock_move_id.location_id.usage in ['supplier','production']:
                                    product_id.with_company(company.id).standard_price_usd = standard_price_usd
                                    #product_id.standard_price = standard_price_usd * new_rate
                        else:
                            product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                            standard_price_usd = product_id.with_company(company.id).standard_price_usd
                            if abs(standard_price_usd) > abs(product_id.with_company(company.id).standard_price):
                                standard_price_usd = product_id.with_company(company.id).standard_price / company.currency_id_dif.inverse_company_rate
                                product_id.with_company(company.id).standard_price_usd = standard_price_usd
                            val['value_usd'] = product_id.qty_available * product_id.standard_price_usd
                else:
                    product_id = self.env['product.product'].search([('id', '=', val['product_id'])])
                    if val.get('stock_move_id'):
                        stock_move_id = self.env['stock.move'].search([('id', '=', val.get('stock_move_id'))])
                        if stock_move_id.location_id.usage in ['supplier','production']:
                            if product_id.with_company(company.id).cost_method == 'average':
                                if product_id.with_company(company.id).standard_price_usd == 0:
                                    product_id.with_company(company.id).standard_price_usd = val['unit_cost_usd']
        else:
            company = self.env['res.company'].browse(vals.get('company_id') or self.env.company.id)
            if 'stock_move_id' in vals and company.return_actual_cost:
                stock_move_id = self.env['stock.move'].search([('id', '=', vals['stock_move_id'])])
                #verificar si el tipo de operacion es de entrada y si posee en el picking_id el grupo se aprovisiona y si tiene dentro de ese grupo una orden de venta
                if stock_move_id.picking_id.picking_type_id.code == 'incoming' and stock_move_id.picking_id.group_id and stock_move_id.picking_id.group_id.sale_id:
                    #reeemplazar los valores de value, unit_cost, remaining_value
                    product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
                    if product_id.with_company(company.id).cost_method in ('average', 'fifo'):
                        vals['value'] = product_id.with_company(company.id).standard_price * float(vals['quantity'])
                        vals['unit_cost'] = product_id.with_company(company.id).standard_price
                        vals['remaining_value'] = product_id.with_company(company.id).standard_price * float(vals['quantity'])
                        #reemplaza tambien los valores en dolares
                        vals['value_usd'] = product_id.with_company(company.id).standard_price_usd * float(vals['quantity'])
                        vals['unit_cost_usd'] = product_id.with_company(company.id).standard_price_usd
                        vals['remaining_value_usd'] = product_id.with_company(company.id).standard_price_usd * float(vals['quantity'])
                        if vals['unit_cost'] == 0 or vals['unit_cost_usd'] == 0:
                            raise ValidationError(_("The cost and dollar cost of the product cannot be 0"))
                        new_rate = vals['unit_cost'] / vals['unit_cost_usd']
                        vals['tasa'] = new_rate

            if not 'unit_cost_usd' in vals and not 'value_usd' in vals:
                if 'quantity' in vals:
                    if float(vals['quantity']) != 0:
                        supplier = False
                        product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
                        standard_price_usd = 0
                        # tasa = self.env.company.currency_id_dif
                        new_rate = company.currency_id_dif.inverse_company_rate
                        if 'stock_move_id' in vals:
                            stock_move_id = self.env['stock.move'].search([('id', '=', vals['stock_move_id'])])
                            if stock_move_id:
                                picking_id = stock_move_id.picking_id
                                date = datetime.date.today()
                                if picking_id:
                                    date = picking_id.date_of_transfer or picking_id.create_date
                                new_rate_ids = company.currency_id_dif._get_rates(company,date)
                                if new_rate_ids:
                                    new_rate = 1 / new_rate_ids[company.currency_id_dif.id]
                            if stock_move_id.location_id.usage == 'supplier':
                                supplier = True
                            else:
                                if 'tasa' in vals:
                                    new_rate = vals['tasa']
                            standard_price_usd = float(vals['unit_cost']) / new_rate
                        else:
                            standard_price_usd = product_id.with_company(company.id).standard_price_usd
                        vals['unit_cost_usd'] = round(standard_price_usd,company.currency_id_dif.decimal_places)
                        vals['value_usd'] = float(vals['quantity']) * vals['unit_cost_usd']
                        vals['tasa'] = new_rate
                        if vals.get('stock_move_id'):
                            stock_move_id = self.env['stock.move'].search([('id', '=', vals.get('stock_move_id'))])
                            if stock_move_id.location_id.usage in ['supplier','production']:
                                supplier = True
                                product_id.with_company(company.id).standard_price_usd = standard_price_usd
                                # product_id.standard_price = standard_price_usd * new_rate
                        if product_id.with_company(company.id).cost_method in ('average', 'fifo') and supplier:
                            vals['remaining_value_usd'] = float(vals['quantity']) * standard_price_usd
                    else:
                        # product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
                        # standard_price_usd = product_id.with_company(company.id).standard_price_usd
                        # if abs(standard_price_usd) > abs(product_id.with_company(company.id).standard_price):
                        #     standard_price_usd = product_id.with_company(
                        #         company.id).standard_price / company.currency_id_dif.inverse_company_rate
                        #     product_id.with_company(company.id).standard_price_usd = standard_price_usd
                        # vals['value_usd'] = product_id.qty_available * product_id.standard_price_usd
                        # if float(vals['value']) < 0:
                        vals['value_usd'] = float(vals['value']) / (company.currency_id_dif.inverse_company_rate)
                            #vals['value_usd'] = product_id.with_company(company.id).qty_available * product_id.with_company(company.id).standard_price_usd
            else:
                product_id = self.env['product.product'].search([('id', '=', vals['product_id'])])
                if vals.get('stock_move_id'):
                    stock_move_id = self.env['stock.move'].search([('id', '=', vals.get('stock_move_id'))])
                    if stock_move_id.location_id.usage in ['supplier','production']:
                        if product_id.with_company(company.id).cost_method == 'average':
                            if product_id.with_company(company.id).standard_price_usd == 0:
                                product_id.with_company(company.id).standard_price_usd = vals['unit_cost_usd']
        res = super(StockValuationLayer, self).create(vals)
        for sl in res:
            if sl.stock_move_id:
                if sl.stock_move_id.location_id.usage in ['supplier','production'] and not sl.stock_landed_cost_id:
                    if sl.product_id.with_company(company.id).cost_method == 'average':
                        sl.product_id.with_company(company.id).standard_price_usd = sl.product_id.value_usd_svl / (sl.product_id.with_company(company.id).quantity_svl if sl.product_id.with_company(company.id).quantity_svl > 0 else 1)

        return res

    def corregir_valoracion(self):
        #buscar todos los productos que tengan valoracion en el modelo stock.valuation.layer
        product_ids = self.mapped('product_id')
        company_id = self.env['res.company'].search([('id','=',1)])
        ##print('productos',len(product_ids))
        x = 0
        for p in product_ids:
            # buscar todas las lineas de valoracion de un producto
            valuation_ids = self.search([('product_id', '=', p.id)])
            ##print('cantidad de movimientos para el producto', p.name, len(valuation_ids))
            # busco la tasa del día de la valoracion
            for v in valuation_ids:
                # if v.tasa > 51 or v.tasa < 35 or v.unit_cost_usd==0:
                date_time = v.create_date
                date = date_time.date()
                tasa_dia = v.company_id.currency_id_dif._get_rates(v.company_id, date)
                new_rate = 1 / tasa_dia[v.company_id.currency_id_dif.id]
                v.tasa = new_rate
                v.unit_cost_usd = v.unit_cost / new_rate
                v.value_usd = v.value / new_rate
                if v.account_move_id:
                    v.account_move_id.line_ids.no_calcular = True
                    v.account_move_id.tax_today = new_rate
                    for l in v.account_move_id.line_ids:
                        if l.credit > 0:
                            l.credit_usd = abs(v.value_usd)
                        if l.debit > 0:
                            l.debit_usd = abs(v.value_usd)
                        l._compute_balance_usd()
            value_total_usd = sum(valuation_ids.mapped('value_usd'))

            quantity_total = sum(valuation_ids.mapped('quantity'))
            if quantity_total > 0 and value_total_usd > 0:
                p.standard_price_usd = value_total_usd / quantity_total
            else:
                p.standard_price_usd = p.standard_price / company_id.currency_id_dif.inverse_company_rate
            x += 1
            # #print('faltan',len(product_ids) - x)
            # commit
            # self.env.cr.commit()
        return True

    def corregir_valoracion_extra_tasa(self):
        #se corregi en amanecer la anglosajona y el ajuste generado por la factura de compra
        account_move_line_ids = self.env['account.move.line'].search([('display_type', '=', 'cogs'),('move_type', '=', 'out_invoice')])
        product_ids = account_move_line_ids.mapped('product_id')
        for p in product_ids:
            for c in self.env['res.company'].search([('id','>',1)]):
                ajustar_cogs = True
                #buscar todos los registros de este producto para todas las compañias y sucursales
                # valuation_ids = self.sudo().search([('product_id', '=', p.id),('quantity','=',0),('value_usd','=',0),('company_id','=',c.id)])
                # for v in valuation_ids:
                #     #buscar el asiento contable y cancelar y eliminar
                #     if v.account_move_id:
                #         v.account_move_id.button_cancel()
                #         v.account_move_id.unlink()
                #     v.unlink()
                #     ajustar_cogs = True
                if ajustar_cogs:
                    valuation_ids = self.search([('product_id', '=', p.id),('company_id','=',c.id),('create_date','<','2025-01-01')])
                    value_total = sum(valuation_ids.mapped('value'))
                    value_total_usd = sum(valuation_ids.mapped('value_usd'))
                    quantity_total = sum(valuation_ids.mapped('quantity'))
                    standard_price = value_total / quantity_total if quantity_total > 0 and value_total > 0 else p.standard_price
                    standard_price_usd = p.standard_price_usd if p.standard_price_usd >0 else standard_price / c.currency_id_dif.inverse_company_rate
                    standard_price_usd = value_total_usd / quantity_total if quantity_total > 0 and value_total_usd > 0 else standard_price_usd
                    # if quantity_total > 0 and value_total > 0:
                    #     p.with_company(c.id).with_context(disable_auto_svl=True).standard_price = value_total / quantity_total
                    #     standard_price = value_total / quantity_total
                    # else:
                    #     p.with_company(c.id).with_context(disable_auto_svl=True).standard_price = p.with_company(c.id).standard_price_usd * c.currency_id_dif.inverse_company_rate
                    #     standard_price = p.with_company(c.id).standard_price_usd * c.currency_id_dif.inverse_company_rate

                    #corrregir las lineas tipo cogs en todas las ventas
                    #buscar todos los apuntes contables de facturas de ventas que sean del tipo cogs y que tengan ese producto
                    account_move_line_ids = self.env['account.move.line'].search([('product_id', '=', p.id),('display_type','=','cogs'),('company_id','=',c.id),('move_type','=','out_invoice')])
                    for l in account_move_line_ids:
                        #buscar la tasa de la fecha del asiento
                        if l.credit > 0:
                            #ejecutar un sql actualizando el campo credit, credit_usd, amount_currency, balance, balance_usd
                            sql = "update account_move_line set credit = %s, credit_usd = %s, amount_currency = %s, balance = %s, balance_usd = %s where id = %s" % (l.quantity * standard_price, l.quantity * standard_price_usd, l.quantity * standard_price * -1, l.quantity * standard_price * -1, l.quantity * standard_price_usd * -1, l.id)
                            self.env.cr.execute(sql)
                        if l.debit > 0:
                            sql = "update account_move_line set debit = %s, debit_usd = %s, amount_currency = %s, balance = %s, balance_usd = %s where id = %s" % (l.quantity * standard_price, l.quantity * standard_price_usd, l.quantity * standard_price, l.quantity * standard_price, l.quantity * standard_price_usd, l.id)
                            self.env.cr.execute(sql)



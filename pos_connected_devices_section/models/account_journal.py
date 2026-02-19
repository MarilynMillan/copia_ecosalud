# coding: utf-8

from odoo import fields, models, api


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection([('sale', 'Ventas'), ('sale_refund', 'Reembolso de venta'), ('purchase', 'Compras'),
                            ('purchase_refund', 'Reembolso de compra'), ('cash', 'Efectivo'), ('bank', 'Banco'),
                            ('general', 'Varios'), ('situation', 'Situacion de Apertura/Cierre'),
                            ('sale_debit', 'Débito de venta'), ('purchase_debit', 'Débito de compra')], string='Tipo',
                            size=32, required=True,
                            help="Seleccione 'Venta' para los diarios de facturas de clientes. "
                                 "Seleccione 'Compra' para los diarios de facturas de proveedores."
                                 "Seleccione 'Efectivo' o 'Banco' para los diarios que se utilizan en"
                                 "pagos de clientes o proveedores."
                                 " Seleccione 'General' para diarios de operaciones diversas."
                                 " Seleccione 'Situación de apertura / cierre' para las entradas generadas "
                                 " para nuevos años fiscales."
                                 " Seleccione 'Débito de venta' para los diarios de notas de débito del cliente."
                                 " Seleccione 'Débito de compra' para los diarios de notas de débito del proveedor.")

    default_iva_account = fields.Many2one('account.account', string='Cuenta retención IVA')
    default_islr_account = fields.Many2one('account.account', string='Cuenta retención ISLR')
    is_iva_journal = fields.Boolean(default=False)
    is_islr_journal = fields.Boolean(default=False)
    eliminar_impuestos = fields.Boolean(default=False, string="Eliminar impuestos")
    permitir_itf = fields.Boolean(default=False, string="Permitir ITF")

    # txt file fields.
    name_file_txt = fields.Char(string="File Name")

    sequence_nro_ctrl_id = fields.Many2one('ir.sequence', string='Secuencia Nro de Control',
                                  help="This field contains the information related to the numbering of the"
                                       " journal entries of this journal.",
                                  copy=False, domain="[('company_id', '=', company_id)]")
    sequence_nro_ctrl_next = fields.Integer(string='Próximo Nro de Control',
                                          help='The next sequence number will be used for the next invoice.',
                                          compute='_compute_seq_number_next', )
    nro_ctrl_desde = fields.Integer(string='Nro de Control Desde', help='Número de control desde')
    nro_ctrl_hasta = fields.Integer(string='Nro de Control Hasta', help='Número de control hasta')

    credit_note_journal_id = fields.Many2one('account.journal', string='Diario de Notas de Crédito',
                                             help='Diario de notas de crédito para el diario de ventas')

    @api.depends('sequence_nro_ctrl_id.use_date_range', 'sequence_nro_ctrl_id.number_next_actual')
    def _compute_seq_number_next(self):
        '''Compute 'sequence_number_next' according to the current sequence in use,
        an ir.sequence or an ir.sequence.date_range.
        '''
        for journal in self:
            if journal.sequence_nro_ctrl_id:
                sequence = journal.sequence_nro_ctrl_id._get_current_sequence()
                journal.sequence_nro_ctrl_next = sequence.number_next_actual
            else:
                journal.sequence_nro_ctrl_next = 1

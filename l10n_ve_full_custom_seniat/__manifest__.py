{
    'name': 'Homologación Fiscal Venezuela (SENIAT)',
    'version': '17.0.3.0.6',
    'category': 'Accounting/Localizations',
    'author': 'Nayliover Espinoza / BlackERPCCS, C.A.',
    'website': 'mailto:naylioverespinoza@gmail.com',
    'summary': 'Homologación fiscal, IGTF, Retenciones y Validaciones SENIAT',
    'description': """
        Módulo de Homologación de la Localización Fiscal para Venezuela.
    """,
    'depends': [
        'base', 'account', 'sale', 'account_dual_currency', 'l10n_ve_full', 'account_debit_note'
    ],
    'data': [
        'security/seniat_security.xml',
        'security/ir.model.access.csv',
        'data/account_move_server_actions.xml',
        # 'data/annulment_reasons_data.xml',
        'wizard/account_payment_register_seniat_view.xml',
        'views/account_annulment_reason_view.xml',
        'views/account_move_reset_wizard_view.xml',
        'views/sale_order_invoice_warning_view.xml',
        'views/account_payment_seniat_view.xml',
        'views/account_move_seniat_view.xml',
        'views/sale_order_dual_currency_view.xml',
        'views/report_sale_custom.xml',
        'views/web_login_view.xml',
        'views/res_config_settings_view.xml',
    ],
    'images': ['static/description/icon.png'],
    'installable': True,
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
{
    'name': "Venezuela: POS Sale Book",

    'summary': """
        Localización Venezolana""",
    'description': """
        Inclusión de ventas POS al libro de ventas

    """,
    'author': 'José Luis Vizcaya López',
    'company': 'José Luis Vizcaya López',
    'maintainer': 'José Luis Vizcaya López',
    'website': 'https://vizcaya.mi-erp.app',
    'category': 'Localization',
    'version': '17.0.1.2.0',
    'depends': ['point_of_sale', 'l10n_ve_full','pos_fiscal_printer'],
    'data': [
        'views/account_fiscal_book.xml',
        'report/account_fiscal_book_report.xml',
    ],
    "license": "GPL-2",
    "price": 500,
    "currency": "USD",
}

# -*- coding: utf-8 -*-
{
    'name': 'Venezuela: POS IGTF',
    'version': '17.0.1.0.0',
    'author': 'José Luis Vizcaya López',
    'company': 'José Luis Vizcaya López',
    'maintainer': 'José Luis Vizcaya López',
    'website': 'https://github.com/birkot',
    'category': 'Sales/Point of Sale',
    'summary': 'IGTF en el POS',
    'depends': ['point_of_sale','pos_show_dual_currency'],
    'data': [
        'views/inherited_views.xml',
    ],
    'assets': {
        'point_of_sale.assets': [
            'pos_igtf_tax/static/src/scss/**/*',
            'pos_igtf_tax/static/src/xml/**/*',
            'pos_igtf_tax/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
{
    "name": """Venezuela: POS show dual currency""",
    "summary": """Adds price of other currency at products in POS""",
    "category": "Point Of Sale",
    "version": "17.0.1.0.2",
    'author': 'Nayliover espinoza',
    'license': 'AGPL-3',
    'depends': [
        'point_of_sale', 'pos_sale',
    ],
    'data': [
        'views/views.xml',
        'views/res_config_settings.xml',
        'views/pos_config.xml',
        'views/pos_order.xml',
        'views/pos_payment.xml',
        'views/pos_payment_method.xml',
        'views/pos_session.xml',
        'views/report_saledetails.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'assets': {
        'point_of_sale._assets_pos': [
            # 1. ESTILOS (CSS)
            #'pos_show_dual_currency/static/src/css/pos.css',

            # 2. LÓGICA JAVASCRIPT
            'pos_show_dual_currency/static/src/js/models.js',
            'pos_show_dual_currency/static/src/js/product_card.js',
            'pos_show_dual_currency/static/src/js/utils/ref_rate.js',
            #'pos_show_dual_currency/static/src/js/ChromePatch.js',
            #'pos_show_dual_currency/static/src/js/ChromeWidgets/TRM.js',
            'pos_show_dual_currency/static/src/js/ChromeWidgets/CashMoveButton.js',
            #'pos_show_dual_currency/static/src/js/OrderManagementScreen/SaleOrderRow.js',
            'pos_show_dual_currency/static/src/js/OrderWidget.js',
            'pos_show_dual_currency/static/src/js/Screens/PaymentScreen/PaymentScreenPaymentLines.js',
            'pos_show_dual_currency/static/src/js/Screens/PaymentScreen/PaymentScreenStatus.js',
            #'pos_show_dual_currency/static/src/js/TicketScreen/TicketScreen.js',
            #'pos_show_dual_currency/static/src/js/Popups/CashMovePopup.js',
            #'pos_show_dual_currency/static/src/js/Popups/CashOpeningPopup.js',
            'pos_show_dual_currency/static/src/js/Popups/ClosePosPopup.js',
            'pos_show_dual_currency/static/src/js/Popups/MoneyDetailsPopup.js',

            # 3. VISTAS XML
            #'pos_show_dual_currency/static/src/xml/ChromeWidgets/TRM.xml',
            'pos_show_dual_currency/static/src/xml/ChromeWidgets/CashMoveButton.xml',
            #'pos_show_dual_currency/static/src/xml/OrderManagementScreen/SaleOrderRow.xml',
            #'pos_show_dual_currency/static/src/xml/Popups/CashMovePopup.xml',
            #'pos_show_dual_currency/static/src/xml/Popups/CashOpeningPopup.xml',
            'pos_show_dual_currency/static/src/xml/Popups/ClosePosPopup.xml',
            'pos_show_dual_currency/static/src/xml/Popups/MoneyDetailsPopup.xml',
            #'pos_show_dual_currency/static/src/xml/Popups/ProductConfiguratorPopup.xml',
            'pos_show_dual_currency/static/src/xml/Screens/PaymentScreen/PaymentScreenPaymentLines.xml',
            'pos_show_dual_currency/static/src/xml/Screens/PaymentScreen/PaymentScreenStatus.xml',
            #'pos_show_dual_currency/static/src/xml/TicketScreen/TicketScreen.xml',
            #'pos_show_dual_currency/static/src/xml/Receipt/OrderReceipt.xml',
            #'pos_show_dual_currency/static/src/xml/Receipt/OrderlineReceipt.xml',
            'pos_show_dual_currency/static/src/xml/pos.xml',
        ],
    },
}

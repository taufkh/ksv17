# -*- coding: utf-8 -*-
{
    'name': 'POS Session Z Report',
    'author': 'Sedari Coffee',
    'version': '17.0.1.0.0',
    'website': 'sedari.arkana.app',
    'category': 'Point Of Sale',
    'summary': 'Laporan Z POS dengan printer Epson & Imin',
    'depends': [
        'base',
        'point_of_sale',
        'pos_epson_printer',
        'pos_bluetooth_printer_android',
    ],
    'data': [
        'report/report_pos_session.xml',
        'views/pos_session_view.xml',
    ],
    'demo': [],
    'license': 'OPL-1',
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_session_z_report_ext_omax/static/src/app/pos_session_report/pos_session_report_patch.js',
            'pos_session_z_report_ext_omax/static/src/app/pos_session_report/pos_session_report.xml',
            'pos_session_z_report_ext_omax/static/src/app/pos_session_report/epson_printer_service.js',
            'pos_session_z_report_ext_omax/static/src/app/screens/session_report_preview_screen/session_report_preview_screen.js',
            'pos_session_z_report_ext_omax/static/src/app/screens/session_report_preview_screen/session_report_preview_screen.xml',
            'pos_session_z_report_ext_omax/static/src/app/screens/session_report_preview_screen/session_report_canvas.js',
            'pos_session_z_report_ext_omax/static/src/app/screens/session_report_preview_screen/session_report_canvas.xml',
        ],
        'web.assets_backend': [
            'pos_session_z_report_ext_omax/static/src/js/session_z_report_button.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'pre_init_hook': 'pre_init_check',
    'module_type': 'official',
}

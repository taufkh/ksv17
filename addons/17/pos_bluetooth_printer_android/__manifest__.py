# -*- coding: utf-8 -*-
{
    "name": "POS Bluetooth Printer Android",
    "summary": "Direct Bluetooth receipt printing from Odoo POS on Android tablets",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_bluetooth_printer_android/static/src/app/printer/bluetooth_escpos_printer.js",
            "pos_bluetooth_printer_android/static/src/app/printer/pos_printer_service_patch.js",
            "pos_bluetooth_printer_android/static/src/app/screens/receipt_screen/receipt_screen_patch.js",
            "pos_bluetooth_printer_android/static/src/app/screens/receipt_screen/receipt_screen_patch.xml",
        ],
    },
    "installable": True,
    "application": False,
}

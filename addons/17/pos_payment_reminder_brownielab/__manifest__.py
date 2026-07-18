{
    "name": "POS Payment Reminder Brownielab",
    "summary": "Show configurable cashier reminder popup after POS payment validation",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payment_reminder_brownielab/static/src/app/popups/payment_reminder_popup.js",
            "pos_payment_reminder_brownielab/static/src/app/popups/payment_reminder_popup.xml",
            "pos_payment_reminder_brownielab/static/src/app/screens/payment_screen/payment_screen_reminder.js",
            "pos_payment_reminder_brownielab/static/src/app/screens/receipt_screen/receipt_screen_reminder.js",
            "pos_payment_reminder_brownielab/static/src/scss/payment_reminder_popup.scss",
        ],
    },
    "installable": True,
    "application": False,
}

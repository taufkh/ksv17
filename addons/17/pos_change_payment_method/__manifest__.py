{
    "name": "POS Change Payment Method",
    "summary": "Controlled payment method correction for paid POS orders",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": [
        "point_of_sale",
        "bakery_user_roles",
        "pos_sale_channel",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_supervisor_pin_views.xml",
        "views/pos_revision_change_log_views.xml",
        "views/pos_backend_payment_revision_views.xml",
        "views/pos_backend_sale_channel_revision_views.xml",
        "views/pos_backend_void_order_views.xml",
        "views/pos_order_revision_log_views.xml",
        "views/pos_payment_method_change_log_views.xml",
        "views/pos_sale_channel_change_log_views.xml",
        "data/cleanup_legacy_revision_menus.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_change_payment_method/static/src/app/store/payment_method_safety.js",
            "pos_change_payment_method/static/src/app/screens/ticket_screen/change_payment_method_button.js",
            "pos_change_payment_method/static/src/app/screens/ticket_screen/change_payment_method_button.xml",
        ],
    },
    "installable": True,
    "application": False,
}

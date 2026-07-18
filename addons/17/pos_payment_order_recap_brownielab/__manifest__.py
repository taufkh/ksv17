{
    "name": "POS Payment Order Recap Brownielab",
    "summary": "Show order item recap on POS payment screen for cashier verification",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payment_order_recap_brownielab/static/src/app/screens/payment_screen/payment_screen_recap.js",
            "pos_payment_order_recap_brownielab/static/src/app/screens/payment_screen/payment_screen_recap.xml",
            "pos_payment_order_recap_brownielab/static/src/scss/payment_screen_recap.scss",
        ],
    },
    "installable": True,
    "application": False,
}

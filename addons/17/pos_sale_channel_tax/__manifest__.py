{
    "name": "POS Sale Channel Tax",
    "summary": "Apply fiscal positions per POS sales channel",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "pos_sale_channel_pricelist"],
    "data": [
        "views/pos_sale_channel_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_sale_channel_tax/static/src/app/store/order_sale_channel_tax.js",
            "pos_sale_channel_tax/static/src/app/screens/receipt_screen/order_receipt_tax_name.xml",
        ],
    },
    "installable": True,
    "application": False,
}

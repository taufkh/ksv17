{
    "name": "POS Line Discount Type",
    "summary": "Add percent or amount discount options per POS order line",
    "version": "17.0.1.0.0",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_line_discount_type/static/src/app/store/orderline_discount_type.js",
            "pos_line_discount_type/static/src/app/screens/product_screen/product_screen.js",
            "pos_line_discount_type/static/src/xml/orderline.xml",
        ],
    },
    "installable": True,
    "application": False,
}


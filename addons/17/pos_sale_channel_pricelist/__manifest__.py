{
    "name": "POS Sale Channel Pricelist Linker",
    "summary": "Link POS sale channels with pricelists",
    "version": "17.0.1.0.1",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "pos_sale_channel"],
    "data": [
        "views/pos_sale_channel_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_sale_channel_pricelist/static/src/app/store/order_sale_channel_pricelist.js",
        ],
    },
    "installable": True,
    "application": False,
}

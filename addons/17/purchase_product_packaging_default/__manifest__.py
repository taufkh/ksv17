{
    "name": "Purchase Product Packaging Default",
    "version": "17.0.3.0.0",
    "summary": "Default purchase packs and pack pricing on purchase documents",
    "category": "Purchase",
    "license": "LGPL-3",
    "depends": ["purchase", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_packaging_views.xml",
        "views/product_template_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
        "views/purchase_signature_wizard_views.xml",
        "views/report_views.xml",
    ],
    "installable": True,
}

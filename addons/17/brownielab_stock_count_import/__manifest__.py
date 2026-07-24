{
    "name": "Brownielab Stock Count Import",
    "version": "17.0.1.0.0",
    "summary": "Import inventory counts with product-aware packaging resolution",
    "category": "Inventory/Inventory",
    "license": "LGPL-3",
    "depends": ["stock_inventory_packaging"],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_quant_views.xml",
        "views/stock_count_import_wizard_views.xml",
    ],
    "installable": True,
}

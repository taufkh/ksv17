{
    "name": "POS Sales Simulation",
    "version": "17.0.1.0.0",
    "summary": "Backend-only POS sales simulation batches and transactions",
    "category": "Sales/Point of Sale",
    "images": ["static/description/icon.png"],
    "depends": ["point_of_sale"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "report/pos_sales_simulation_report.xml",
        "views/pos_config_views.xml",
        "views/pos_sales_simulation_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}

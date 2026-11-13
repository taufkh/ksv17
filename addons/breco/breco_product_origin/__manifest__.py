{
    'name': 'Breco Product Origin',
    'version': '17.0.1.1.0',
    'category': 'Inventory/Inventory',
    'summary': 'Processor and region master data for products',
    'license': 'LGPL-3',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_origin_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': False,
}

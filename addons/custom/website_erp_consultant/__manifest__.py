{
    'name': 'ERP Consultant Website Theme',
    'version': '17.0.1.0.0',
    'category': 'Website/Theme',
    'summary': 'Professional website theme for ERP consultancy businesses',
    'author': 'Your Company',
    'license': 'LGPL-3',
    'depends': [
        'website',
        'crm',
        'portal',
    ],
    'data': [
        'views/assets.xml',
        'views/snippets/snippets.xml',
        'views/templates/layout.xml',
        'views/templates/home.xml',
        'views/templates/services.xml',
        'views/templates/about.xml',
        'views/templates/contact.xml',
        'data/website_data.xml',
    ],
    # Assets are registered via ir.asset records in views/assets.xml
    # which gives precise control over load order (prepend before Bootstrap).
    # Do NOT also list them here — that would load SCSS twice and break styling.
    'installable': True,
    'auto_install': False,
    'application': False,
}

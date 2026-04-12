{
    "name": "Bakery User Roles",
    "version": "17.0.1.0.0",
    "summary": "Role groups and starter users for bakery operations",
    "category": "Hidden",
    "depends": [
        "base",
        "portal",
        "purchase",
        "stock",
        "mrp",
        "point_of_sale",
        "account",
    ],
    "data": [
        "security/role_groups.xml",
        "security/menu_restrictions.xml",
    ],
    "post_init_hook": "post_init_hook",
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}

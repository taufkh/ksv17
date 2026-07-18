{
    "name": "Brownielab Owner Dashboard",
    "version": "17.0.1.0.0",
    "summary": "Owner-only operational and finance dashboard for Brownielab",
    "category": "Accounting",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "account_accountant",
        "bakery_user_roles",
    ],
    "data": [
        "security/brownielab_owner_dashboard_security.xml",
        "security/ir.model.access.csv",
        "views/brownielab_owner_dashboard_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "brownielab_owner_dashboard/static/src/scss/brownielab_owner_dashboard.scss",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}

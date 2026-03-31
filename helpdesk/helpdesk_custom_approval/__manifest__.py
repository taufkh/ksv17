{
    "name": "Helpdesk Custom Approval",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Approval flow for support exceptions and special service actions",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_ticket_approval_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}


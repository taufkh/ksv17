{
    "name": "Helpdesk Custom Contract",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Support contracts and retainer entitlement for helpdesk tickets",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt_timesheet",
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_support_contract_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}


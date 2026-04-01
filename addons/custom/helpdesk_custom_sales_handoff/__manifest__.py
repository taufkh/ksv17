{
    "name": "Helpdesk Custom Sales Handoff",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Keep Helpdesk support-centric with a separate sales handoff flow",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt_crm",
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_sales_handoff_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/crm_lead_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}

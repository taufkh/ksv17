{
    "name": "Helpdesk Custom Dispatch",
    "summary": "Onsite visit and engineer dispatch workflow for helpdesk tickets",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_approval",
        "helpdesk_custom_demo",
        "helpdesk_mgmt_project",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_dispatch_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

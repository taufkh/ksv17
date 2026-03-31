{
    "name": "Helpdesk Custom Problem Management",
    "summary": "Recurring issue and known error management on top of helpdesk tickets",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_knowledge",
        "helpdesk_custom_escalation",
        "helpdesk_custom_asset_coverage",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_problem_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

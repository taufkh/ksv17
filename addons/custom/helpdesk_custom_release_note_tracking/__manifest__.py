{
    "name": "Helpdesk Custom Release Note Tracking",
    "summary": "Track fixes, rollout notes, and customer communication for helpdesk issues",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_problem_management",
        "helpdesk_custom_customer_communication_log",
        "helpdesk_custom_knowledge",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_release_note_views.xml",
        "views/helpdesk_problem_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/document_page_views.xml",
        "views/helpdesk_communication_log_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

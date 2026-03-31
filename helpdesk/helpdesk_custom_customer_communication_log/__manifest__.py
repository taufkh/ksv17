{
    "name": "Helpdesk Custom Customer Communication Log",
    "summary": "Structured customer communication journal across portal, API, and WhatsApp",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_portal",
        "helpdesk_custom_whatsapp",
        "helpdesk_custom_api",
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_communication_log_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

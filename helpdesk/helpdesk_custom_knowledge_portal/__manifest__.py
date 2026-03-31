{
    "name": "Helpdesk Custom Knowledge Portal",
    "summary": "Customer-facing knowledge publication workflow for helpdesk self-service",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_knowledge",
        "helpdesk_custom_portal",
        "helpdesk_custom_contract",
        "helpdesk_custom_demo",
    ],
    "data": [
        "views/document_page_views.xml",
        "views/helpdesk_portal_templates.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

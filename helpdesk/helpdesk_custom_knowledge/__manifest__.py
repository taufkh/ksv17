{
    "name": "Helpdesk Custom Knowledge",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Helpdesk knowledge base linked directly to support tickets",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "document_page",
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/helpdesk_knowledge_security.xml",
        "views/document_page_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}


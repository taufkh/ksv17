{
    "name": "Helpdesk Custom Customer 360",
    "summary": "Customer-centric 360 support overview across helpdesk modules",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_contract",
        "helpdesk_custom_dispatch",
        "helpdesk_custom_invoice",
        "helpdesk_custom_knowledge",
        "helpdesk_custom_portal",
        "helpdesk_custom_sales_handoff",
    ],
    "data": [
        "views/res_partner_views.xml",
    ],
    "installable": True,
    "application": False,
}

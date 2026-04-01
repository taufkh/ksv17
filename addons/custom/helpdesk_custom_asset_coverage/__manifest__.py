{
    "name": "Helpdesk Custom Asset Coverage",
    "summary": "Support asset, branch, and device coverage linked to contracts and tickets",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_contract",
        "helpdesk_custom_dispatch",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_support_asset_views.xml",
        "views/helpdesk_support_contract_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_dispatch_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

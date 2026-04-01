{
    "name": "Helpdesk Custom Contract Renewal Analytics",
    "summary": "Renewal pipeline analytics, risk overview, and customer renewal insight",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_contract_renewal",
        "helpdesk_custom_customer_360",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_contract_renewal_views.xml",
        "views/helpdesk_contract_renewal_analytics_views.xml",
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

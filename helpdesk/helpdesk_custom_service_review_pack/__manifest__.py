{
    "name": "Helpdesk Custom Service Review Pack",
    "version": "17.0.1.0.0",
    "summary": "Executive customer service review packs and printable support summaries",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_custom_customer_360",
        "helpdesk_custom_customer_communication_log",
        "helpdesk_custom_contract_renewal_analytics",
        "helpdesk_custom_dispatch_execution",
        "helpdesk_custom_invoice",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_service_review_pack_views.xml",
        "views/res_partner_views.xml",
        "report/helpdesk_service_review_pack_report.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

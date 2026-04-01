{
    "name": "Helpdesk Custom Communication Analytics",
    "summary": "Communication responsiveness and channel analytics for helpdesk tickets",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_custom_customer_communication_log",
        "helpdesk_custom_kpi",
        "helpdesk_custom_demo",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_communication_analytics_report_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

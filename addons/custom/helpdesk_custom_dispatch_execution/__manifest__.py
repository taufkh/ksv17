{
    "name": "Helpdesk Custom Dispatch Execution",
    "summary": "Technician execution controls, evidence, and sign-off for dispatches",
    "version": "17.0.1.0.0",
    "category": "Helpdesk",
    "author": "OpenAI",
    "license": "AGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_dispatch",
        "helpdesk_custom_field_service_report",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_dispatch_views.xml",
        "views/helpdesk_field_service_report_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

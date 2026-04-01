{
    "name": "Helpdesk Custom API",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "REST-style API for helpdesk tickets and KPI summary",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_portal",
        "helpdesk_custom_kpi",
        "helpdesk_type",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "auto_install": False,
}

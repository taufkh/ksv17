{
    "name": "Helpdesk Custom Renewal Forecast",
    "version": "17.0.1.0.0",
    "summary": "Renewal forecast versus target and budget dashboard",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_contract_renewal_analytics",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_renewal_target_views.xml",
        "views/helpdesk_renewal_forecast_dashboard_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

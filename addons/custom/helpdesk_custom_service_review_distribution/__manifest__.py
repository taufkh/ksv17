{
    "name": "Helpdesk Custom Service Review Distribution",
    "version": "17.0.1.0.0",
    "summary": "Scheduled distribution for service review packs and executive exports",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_service_review_pack",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/helpdesk_service_review_distribution_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

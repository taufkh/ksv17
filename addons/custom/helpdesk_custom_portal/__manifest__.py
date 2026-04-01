{
    "name": "Helpdesk Custom Portal",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Public tracking portal and enhanced ticket experience",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_escalation",
        "helpdesk_mgmt_rating",
        "helpdesk_portal_restriction",
        "helpdesk_ticket_partner_response",
        "helpdesk_type",
        "website",
    ],
    "assets": {
        "web.assets_frontend": [
            "helpdesk_custom_portal/static/src/scss/helpdesk_custom_portal.scss",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_public_portal_share_wizard_views.xml",
        "views/helpdesk_portal_templates.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

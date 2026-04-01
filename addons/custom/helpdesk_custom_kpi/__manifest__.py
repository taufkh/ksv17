{
    "name": "Helpdesk Custom KPI",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "KPI reporting dashboard for helpdesk tickets",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_escalation",
        "helpdesk_mgmt_sla",
        "helpdesk_mgmt_rating",
        "helpdesk_type",
    ],
    "assets": {
        "web.assets_backend": [
            "helpdesk_custom_kpi/static/src/scss/helpdesk_custom_kpi.scss",
        ],
    },
    "data": [
        "security/ir.model.access.csv",
        "views/helpdesk_ticket_kpi_report_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

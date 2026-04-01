{
    "name": "Helpdesk Custom Escalation",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Escalation engine for helpdesk tickets",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_mgmt",
        "helpdesk_mgmt_sla",
        "mail",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/helpdesk_escalation_rule_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

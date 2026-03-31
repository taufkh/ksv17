# License LGPL-3 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Helpdesk AI Assistant (Claude)",
    "version": "17.0.1.0.0",
    "category": "After-Sales",
    "summary": "Integrate Anthropic Claude AI for automatic ticket triage, customer responses, and developer guidance plans",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["helpdesk_mgmt", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/res_config_settings_views.xml",
        "views/helpdesk_ticket_team_views.xml",
        "views/helpdesk_ai_log_views.xml",
        "views/helpdesk_ticket_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

# -*- coding: utf-8 -*-
{
    "name": "Helpdesk Extended",
    "version": "17.0.1.0.0",
    "summary": "All-in-one helpdesk extension: SLA, types, templates, auto-assign, "
               "ratings, related tickets, merge, project/sale/CRM integration, "
               "timesheets, stage validation, portal restrictions, and more.",
    "author": "Custom",
    "license": "LGPL-3",
    "category": "Helpdesk",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_mgmt",
        "mail",
        "portal",
        "rating",
        "resource",
        "project",
        "sale_management",
        "crm",
        "hr_timesheet",
        "website",
    ],
    "data": [
        # Security
        "security/ir.model.access.csv",
        # Data
        "data/mail_template_data.xml",
        "data/ir_cron_data.xml",
        # Views — base models first
        "views/helpdesk_ticket_type_views.xml",
        "views/helpdesk_ticket_stage_views.xml",
        "views/helpdesk_ticket_team_views.xml",
        "views/helpdesk_sla_views.xml",
        "views/helpdesk_ticket_views.xml",
        "views/helpdesk_ticket_merge_views.xml",
        "views/helpdesk_ticket_create_lead_views.xml",
        "views/project_views.xml",
        "views/sale_order_views.xml",
        "views/crm_lead_views.xml",
        "views/res_config_settings_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}

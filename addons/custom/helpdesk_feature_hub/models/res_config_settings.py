from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_feature_core_extended_enabled = fields.Boolean(
        string="Helpdesk Extended Foundation",
        config_parameter="helpdesk_feature_hub.helpdesk_core_extended.enabled",
        default=True,
    )
    helpdesk_feature_escalation_enabled = fields.Boolean(
        string="Escalation Engine",
        config_parameter="helpdesk_feature_hub.helpdesk_ops_escalation.enabled",
        default=True,
    )
    helpdesk_feature_portal_enabled = fields.Boolean(
        string="Public Tracking Portal",
        config_parameter="helpdesk_feature_hub.helpdesk_channel_portal.enabled",
        default=True,
    )
    helpdesk_feature_whatsapp_enabled = fields.Boolean(
        string="WhatsApp Notifications",
        config_parameter="helpdesk_feature_hub.helpdesk_channel_whatsapp.enabled",
        default=True,
    )
    helpdesk_feature_api_enabled = fields.Boolean(
        string="Helpdesk API",
        config_parameter="helpdesk_feature_hub.helpdesk_integration_api.enabled",
        default=True,
    )
    helpdesk_feature_claude_ai_enabled = fields.Boolean(
        string="Claude AI",
        config_parameter="helpdesk_feature_hub.helpdesk_ai_claude.enabled",
        default=True,
    )
    helpdesk_feature_invoice_enabled = fields.Boolean(
        string="Billing and Invoicing",
        config_parameter="helpdesk_feature_hub.helpdesk_billing_invoice.enabled",
        default=True,
    )
    helpdesk_feature_dispatch_enabled = fields.Boolean(
        string="Dispatch Workflow",
        config_parameter="helpdesk_feature_hub.helpdesk_ops_dispatch.enabled",
        default=True,
    )
    helpdesk_feature_dispatch_execution_enabled = fields.Boolean(
        string="Dispatch Execution",
        config_parameter="helpdesk_feature_hub.helpdesk_ops_dispatch_execution.enabled",
        default=True,
    )
    helpdesk_feature_field_service_report_enabled = fields.Boolean(
        string="Field Service Report",
        config_parameter="helpdesk_feature_hub.helpdesk_ops_field_service_report.enabled",
        default=True,
    )
    helpdesk_feature_contract_renewal_enabled = fields.Boolean(
        string="Contract Renewal Watch",
        config_parameter="helpdesk_feature_hub.helpdesk_renewal_watch.enabled",
        default=True,
    )
    helpdesk_feature_kpi_enabled = fields.Boolean(
        string="KPI Reporting",
        config_parameter="helpdesk_feature_hub.helpdesk_analytics_kpi.enabled",
        default=True,
    )
    helpdesk_feature_communication_analytics_enabled = fields.Boolean(
        string="Communication Analytics",
        config_parameter="helpdesk_feature_hub.helpdesk_analytics_communication.enabled",
        default=True,
    )
    helpdesk_feature_customer_360_enabled = fields.Boolean(
        string="Customer Support Overview",
        config_parameter="helpdesk_feature_hub.helpdesk_customer_overview.enabled",
        default=True,
    )
    helpdesk_feature_renewal_analytics_enabled = fields.Boolean(
        string="Renewal Analytics",
        config_parameter="helpdesk_feature_hub.helpdesk_renewal_analytics.enabled",
        default=True,
    )
    helpdesk_feature_renewal_forecast_enabled = fields.Boolean(
        string="Renewal Forecast",
        config_parameter="helpdesk_feature_hub.helpdesk_renewal_forecast.enabled",
        default=True,
    )
    helpdesk_feature_service_review_pack_enabled = fields.Boolean(
        string="Service Review Pack",
        config_parameter="helpdesk_feature_hub.helpdesk_review_pack.enabled",
        default=True,
    )
    helpdesk_feature_customer_success_playbook_enabled = fields.Boolean(
        string="Customer Success Playbooks",
        config_parameter="helpdesk_feature_hub.helpdesk_success_playbook.enabled",
        default=True,
    )
    helpdesk_feature_service_review_distribution_enabled = fields.Boolean(
        string="Service Review Distribution",
        config_parameter="helpdesk_feature_hub.helpdesk_review_distribution.enabled",
        default=True,
    )

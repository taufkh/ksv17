from odoo import _, api, models
from odoo.exceptions import UserError


FEATURE_DEFINITIONS = {
    "helpdesk.core.extended": {
        "label": "Helpdesk Extended Foundation",
        "config_parameter": "helpdesk_feature_hub.helpdesk_core_extended.enabled",
        "default_enabled": True,
    },
    "helpdesk.calendar": {
        "label": "Ticket Calendar",
        "config_parameter": "helpdesk_feature_hub.helpdesk_calendar.enabled",
        "default_enabled": True,
    },
    "helpdesk.ops.escalation": {
        "label": "Escalation Engine",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ops_escalation.enabled",
        "default_enabled": True,
    },
    "helpdesk.analytics.kpi": {
        "label": "KPI Reporting",
        "config_parameter": "helpdesk_feature_hub.helpdesk_analytics_kpi.enabled",
        "default_enabled": True,
    },
    "helpdesk.channel.portal": {
        "label": "Public Tracking Portal",
        "config_parameter": "helpdesk_feature_hub.helpdesk_channel_portal.enabled",
        "default_enabled": True,
    },
    "helpdesk.channel.whatsapp": {
        "label": "WhatsApp Notifications",
        "config_parameter": "helpdesk_feature_hub.helpdesk_channel_whatsapp.enabled",
        "default_enabled": True,
    },
    "helpdesk.integration.api": {
        "label": "Helpdesk API",
        "config_parameter": "helpdesk_feature_hub.helpdesk_integration_api.enabled",
        "default_enabled": True,
    },
    "helpdesk.ai.claude": {
        "label": "Claude AI",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ai_claude.enabled",
        "default_enabled": True,
        "team_field": "ai_enabled",
    },
    "helpdesk.ops.approval": {
        "label": "Approval Flow",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ops_approval.enabled",
        "default_enabled": True,
    },
    "helpdesk.billing.invoice": {
        "label": "Billing and Invoicing",
        "config_parameter": "helpdesk_feature_hub.helpdesk_billing_invoice.enabled",
        "default_enabled": True,
        "team_field": "allow_billing",
    },
    "helpdesk.knowledge.base": {
        "label": "Knowledge Base",
        "config_parameter": "helpdesk_feature_hub.helpdesk_knowledge_base.enabled",
        "default_enabled": True,
    },
    "helpdesk.knowledge.portal": {
        "label": "Portal Knowledge",
        "config_parameter": "helpdesk_feature_hub.helpdesk_knowledge_portal.enabled",
        "default_enabled": True,
    },
    "helpdesk.contract.base": {
        "label": "Support Contracts",
        "config_parameter": "helpdesk_feature_hub.helpdesk_contract_base.enabled",
        "default_enabled": True,
    },
    "helpdesk.ops.dispatch": {
        "label": "Dispatch Workflow",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ops_dispatch.enabled",
        "default_enabled": True,
    },
    "helpdesk.ops.dispatch_execution": {
        "label": "Dispatch Execution",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ops_dispatch_execution.enabled",
        "default_enabled": True,
    },
    "helpdesk.ops.field_service_report": {
        "label": "Field Service Report",
        "config_parameter": "helpdesk_feature_hub.helpdesk_ops_field_service_report.enabled",
        "default_enabled": True,
    },
    "helpdesk.customer.overview": {
        "label": "Customer 360",
        "config_parameter": "helpdesk_feature_hub.helpdesk_customer_overview.enabled",
        "default_enabled": True,
    },
    "helpdesk.asset.coverage": {
        "label": "Asset Coverage",
        "config_parameter": "helpdesk_feature_hub.helpdesk_asset_coverage.enabled",
        "default_enabled": True,
    },
    "helpdesk.problem.management": {
        "label": "Problem Management",
        "config_parameter": "helpdesk_feature_hub.helpdesk_problem_management.enabled",
        "default_enabled": True,
    },
    "helpdesk.customer.communication_log": {
        "label": "Customer Communication Log",
        "config_parameter": "helpdesk_feature_hub.helpdesk_customer_communication_log.enabled",
        "default_enabled": True,
    },
    "helpdesk.analytics.communication": {
        "label": "Communication Analytics",
        "config_parameter": "helpdesk_feature_hub.helpdesk_analytics_communication.enabled",
        "default_enabled": True,
    },
    "helpdesk.release.notes": {
        "label": "Release Note Tracking",
        "config_parameter": "helpdesk_feature_hub.helpdesk_release_notes.enabled",
        "default_enabled": True,
    },
    "helpdesk.sales.handoff": {
        "label": "Sales Handoff",
        "config_parameter": "helpdesk_feature_hub.helpdesk_sales_handoff.enabled",
        "default_enabled": True,
    },
    "helpdesk.renewal.watch": {
        "label": "Contract Renewal Watch",
        "config_parameter": "helpdesk_feature_hub.helpdesk_renewal_watch.enabled",
        "default_enabled": True,
    },
    "helpdesk.renewal.analytics": {
        "label": "Renewal Analytics",
        "config_parameter": "helpdesk_feature_hub.helpdesk_renewal_analytics.enabled",
        "default_enabled": True,
    },
    "helpdesk.renewal.forecast": {
        "label": "Renewal Forecast",
        "config_parameter": "helpdesk_feature_hub.helpdesk_renewal_forecast.enabled",
        "default_enabled": True,
    },
    "helpdesk.success.playbook": {
        "label": "Customer Success Playbooks",
        "config_parameter": "helpdesk_feature_hub.helpdesk_success_playbook.enabled",
        "default_enabled": True,
    },
    "helpdesk.review.pack": {
        "label": "Service Review Pack",
        "config_parameter": "helpdesk_feature_hub.helpdesk_review_pack.enabled",
        "default_enabled": True,
    },
    "helpdesk.review.distribution": {
        "label": "Service Review Distribution",
        "config_parameter": "helpdesk_feature_hub.helpdesk_review_distribution.enabled",
        "default_enabled": True,
    },
    "helpdesk.demo.seed": {
        "label": "Demo Seed Data",
        "config_parameter": "helpdesk_feature_hub.helpdesk_demo_seed.enabled",
        "default_enabled": True,
    },
}


class HelpdeskFeatureConfig(models.AbstractModel):
    _name = "helpdesk.feature.config"
    _description = "Helpdesk Feature Configuration"

    @api.model
    def _get_feature_definitions(self):
        return FEATURE_DEFINITIONS

    @api.model
    def _get_feature_definition(self, feature_key):
        return self._get_feature_definitions().get(feature_key, {})

    @api.model
    def _get_feature_param_key(self, feature_key):
        feature = self._get_feature_definition(feature_key)
        return feature.get(
            "config_parameter",
            "helpdesk_feature_hub.%s.enabled" % feature_key.replace(".", "_"),
        )

    @api.model
    def get_label(self, feature_key):
        return self._get_feature_definition(feature_key).get("label", feature_key)

    @api.model
    def is_enabled(self, feature_key, default=None):
        feature = self._get_feature_definition(feature_key)
        if default is None:
            default = feature.get("default_enabled", True)
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(self._get_feature_param_key(feature_key))
        )
        if value in (None, ""):
            return default
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @api.model
    def is_enabled_for_team(self, feature_key, team=False, team_field=None, default=None):
        if team_field is None:
            team_field = self._get_feature_definition(feature_key).get("team_field")
        if not self.is_enabled(feature_key, default=default):
            return False
        if not team or not team_field or team_field not in team._fields:
            return True
        team.ensure_one()
        return bool(team[team_field])

    @api.model
    def ensure_enabled(self, feature_key, message=None, default=None):
        if self.is_enabled(feature_key, default=default):
            return True
        raise UserError(
            message
            or _("%(feature)s is disabled in Helpdesk feature settings.")
            % {"feature": self.get_label(feature_key)}
        )

    @api.model
    def ensure_enabled_for_team(
        self, feature_key, team=False, team_field=None, message=None, default=None
    ):
        self.ensure_enabled(feature_key, default=default)
        if self.is_enabled_for_team(
            feature_key, team=team, team_field=team_field, default=default
        ):
            return True
        raise UserError(
            message
            or _("%(feature)s is not enabled for team %(team)s.")
            % {
                "feature": self.get_label(feature_key),
                "team": team.display_name if team else _("Unknown Team"),
            }
        )

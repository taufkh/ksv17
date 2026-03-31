from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_public_tracking_enabled = fields.Boolean(
        string="Enable Public Tracking Links",
        config_parameter="helpdesk_custom_portal.public_tracking_enabled",
        default=True,
    )
    helpdesk_public_token_validity_days = fields.Integer(
        string="Public Link Validity (Days)",
        config_parameter="helpdesk_custom_portal.public_token_validity_days",
        default=30,
    )
    helpdesk_public_allowed_extensions = fields.Char(
        string="Allowed Attachment Extensions",
        config_parameter="helpdesk_custom_portal.allowed_extensions",
        default="pdf,png,jpg,jpeg,txt,csv,xlsx,docx,zip",
    )
    helpdesk_public_max_attachment_mb = fields.Float(
        string="Maximum Attachment Size (MB)",
        config_parameter="helpdesk_custom_portal.max_attachment_mb",
        default=10.0,
    )
    helpdesk_public_digest_retry_minutes = fields.Integer(
        string="Digest Retry Interval (Minutes)",
        config_parameter="helpdesk_custom_portal.digest_retry_minutes",
        default=60,
    )
    helpdesk_public_digest_max_failures = fields.Integer(
        string="Digest Max Retry Attempts",
        config_parameter="helpdesk_custom_portal.digest_max_failures",
        default=5,
    )
    helpdesk_public_escalation_cooldown_minutes = fields.Integer(
        string="Escalation Cooldown (Minutes)",
        config_parameter="helpdesk_custom_portal.escalation_cooldown_minutes",
        default=120,
    )
    helpdesk_public_csat_low_score_threshold = fields.Integer(
        string="Low CSAT Threshold",
        config_parameter="helpdesk_custom_portal.csat_low_score_threshold",
        default=3,
    )
    helpdesk_public_csat_recovery_due_hours = fields.Integer(
        string="Low CSAT Recovery Due (Hours)",
        config_parameter="helpdesk_custom_portal.csat_recovery_due_hours",
        default=4,
    )
    helpdesk_public_customer_followup_reminder_hours = fields.Integer(
        string="Customer Follow-up Reminder (Hours)",
        config_parameter="helpdesk_custom_portal.customer_followup_reminder_hours",
        default=24,
    )

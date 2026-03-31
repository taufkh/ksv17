from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_whatsapp_enabled = fields.Boolean(
        string="Enable WhatsApp Notifications",
        config_parameter="helpdesk_custom_whatsapp.enabled",
        default=True,
    )
    helpdesk_whatsapp_sandbox_mode = fields.Boolean(
        string="Sandbox Mode",
        config_parameter="helpdesk_custom_whatsapp.sandbox_mode",
        default=True,
    )
    helpdesk_whatsapp_api_url = fields.Char(
        string="API Base URL",
        config_parameter="helpdesk_custom_whatsapp.api_url",
        default="https://graph.facebook.com/v20.0",
    )
    helpdesk_whatsapp_phone_number_id = fields.Char(
        string="Phone Number ID",
        config_parameter="helpdesk_custom_whatsapp.phone_number_id",
    )
    helpdesk_whatsapp_access_token = fields.Char(
        string="Access Token",
        config_parameter="helpdesk_custom_whatsapp.access_token",
    )
    helpdesk_whatsapp_default_country_code = fields.Char(
        string="Default Country Code",
        config_parameter="helpdesk_custom_whatsapp.default_country_code",
        default="+62",
    )
    helpdesk_whatsapp_max_attempts = fields.Integer(
        string="Maximum Attempts",
        config_parameter="helpdesk_custom_whatsapp.max_attempts",
        default=3,
    )
    helpdesk_whatsapp_retry_interval_minutes = fields.Integer(
        string="Retry Interval (Minutes)",
        config_parameter="helpdesk_custom_whatsapp.retry_interval_minutes",
        default=15,
    )

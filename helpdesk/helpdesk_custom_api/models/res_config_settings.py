from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_api_enabled = fields.Boolean(
        string="Enable Helpdesk API",
        config_parameter="helpdesk_custom_api.enabled",
    )
    helpdesk_api_token = fields.Char(
        string="API Bearer Token",
        config_parameter="helpdesk_custom_api.token",
    )
    helpdesk_api_allow_attachment_upload = fields.Boolean(
        string="Allow Attachment Upload",
        config_parameter="helpdesk_custom_api.allow_attachment_upload",
    )
    helpdesk_api_max_attachment_mb = fields.Float(
        string="Max Attachment Size (MB)",
        config_parameter="helpdesk_custom_api.max_attachment_mb",
    )
    helpdesk_api_default_team_id = fields.Many2one(
        comodel_name="helpdesk.ticket.team",
        string="Default API Team",
        config_parameter="helpdesk_custom_api.default_team_id",
        domain=[("active", "=", True)],
    )

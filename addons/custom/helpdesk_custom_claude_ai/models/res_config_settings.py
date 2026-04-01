from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    helpdesk_claude_api_key = fields.Char(
        string="Claude API Key",
        config_parameter="helpdesk_claude.api_key",
        help="Anthropic API key. Get one at https://console.anthropic.com/",
    )
    helpdesk_claude_model = fields.Selection(
        selection=[
            ("claude-opus-4-6", "Claude Opus 4 (Most capable)"),
            ("claude-sonnet-4-6", "Claude Sonnet 4 (Balanced)"),
            ("claude-haiku-4-5-20251001", "Claude Haiku (Fastest / cheapest)"),
        ],
        string="Claude Model",
        config_parameter="helpdesk_claude.model",
        default="claude-sonnet-4-6",
        help="Choose the Claude model to use for ticket analysis. "
             "Sonnet offers the best balance of quality and cost for helpdesk use.",
    )

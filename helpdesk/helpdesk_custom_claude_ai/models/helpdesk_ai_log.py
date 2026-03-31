import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class HelpdeskAiLog(models.Model):
    """Audit trail for every Claude API call made against a ticket."""
    _name = "helpdesk.ai.log"
    _description = "Helpdesk AI Analysis Log"
    _order = "create_date desc"
    _rec_name = "ticket_id"

    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
        index=True,
    )
    classification = fields.Selection(
        selection=[
            ("CONFIGURATION_QUERY", "Configuration Query"),
            ("BUG_REPORT", "Bug Report"),
            ("FEATURE_REQUEST", "Feature Request"),
            ("OTHER", "Other"),
        ],
        string="Classification",
    )
    confidence = fields.Float(string="Confidence", digits=(3, 2))
    model_used = fields.Char(string="Claude Model")
    prompt_tokens = fields.Integer(string="Prompt Tokens")
    completion_tokens = fields.Integer(string="Completion Tokens")
    duration_ms = fields.Integer(string="Duration (ms)")
    response_summary = fields.Text(string="Summary")
    error = fields.Text(string="Error (if any)")
    trigger = fields.Selection(
        selection=[
            ("auto", "Automatic (Cron)"),
            ("manual", "Manual (Button)"),
            ("webhook", "Webhook"),
        ],
        string="Trigger",
        default="auto",
    )

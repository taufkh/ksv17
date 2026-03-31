from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskAiAnalyzeWizard(models.TransientModel):
    """
    Wizard that shows the AI analysis result after a manual trigger.
    Also allows the agent to choose whether to post the response / dev plan.
    """
    _name = "helpdesk.ai.analyze.wizard"
    _description = "Helpdesk AI Analysis Result"

    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="Ticket",
        required=True,
        readonly=True,
    )

    # ── Result display ────────────────────────────────────────────────────────
    ai_status = fields.Selection(related="ticket_id.ai_status", string="AI Status")
    ai_classification = fields.Selection(
        related="ticket_id.ai_classification", string="Classification"
    )
    ai_confidence = fields.Float(
        related="ticket_id.ai_confidence", string="Confidence"
    )
    ai_summary = fields.Char(related="ticket_id.ai_summary", string="Summary")
    ai_estimated_hours = fields.Float(
        related="ticket_id.ai_estimated_hours", string="Estimated Hours"
    )
    ai_affected_modules = fields.Char(
        related="ticket_id.ai_affected_modules", string="Affected Modules"
    )
    ai_response = fields.Html(related="ticket_id.ai_response", string="Customer Response")
    ai_dev_plan = fields.Html(related="ticket_id.ai_dev_plan", string="Development Plan")

    # ── Post options ──────────────────────────────────────────────────────────
    post_response = fields.Boolean(
        string="Post Response to Customer",
        default=True,
        help="Post Claude's answer as a public message the customer can see via portal.",
    )
    post_dev_plan = fields.Boolean(
        string="Post Dev Plan as Internal Note",
        default=True,
        help="Post the development plan as an internal agent note.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        if active_id:
            res["ticket_id"] = active_id
        return res

    def action_post_and_close(self):
        self.ensure_one()
        ticket = self.ticket_id
        if self.post_response and ticket.ai_response:
            ticket._post_ai_customer_response()
        if self.post_dev_plan and ticket.ai_dev_plan:
            ticket._post_dev_plan_internal_note(
                "BUG_REPORT" if ticket.ai_classification == "bug" else "FEATURE_REQUEST",
                ticket.ai_estimated_hours,
                ticket.ai_affected_modules.split(", ") if ticket.ai_affected_modules else [],
            )
        return {"type": "ir.actions.act_window_close"}

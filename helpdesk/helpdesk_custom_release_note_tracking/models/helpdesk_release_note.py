from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskReleaseNote(models.Model):
    _name = "helpdesk.release.note"
    _description = "Helpdesk Release Note"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "release_date desc, id desc"

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("rolled_out", "Rolled Out"),
            ("communicated", "Communicated"),
            ("closed", "Closed"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    release_type = fields.Selection(
        [
            ("hotfix", "Hotfix"),
            ("patch", "Patch"),
            ("maintenance", "Maintenance"),
            ("feature", "Feature"),
        ],
        default="patch",
        required=True,
        tracking=True,
    )
    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
        tracking=True,
    )

    name = fields.Char(required=True, tracking=True)
    version = fields.Char(required=True, tracking=True)
    release_date = fields.Date(tracking=True)
    communication_due_date = fields.Date(tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    team_id = fields.Many2one("helpdesk.ticket.team", tracking=True)
    owner_id = fields.Many2one(
        "res.users",
        string="Release Owner",
        default=lambda self: self.env.user,
        tracking=True,
        domain=[("share", "=", False)],
    )
    summary = fields.Text(required=True)
    technical_notes = fields.Html()
    rollout_notes = fields.Html()
    customer_message = fields.Html()
    problem_ids = fields.Many2many(
        "helpdesk.problem",
        "helpdesk_problem_release_note_rel",
        "release_note_id",
        "problem_id",
        string="Problem Records",
    )
    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_release_note_ticket_rel",
        "release_note_id",
        "ticket_id",
        string="Impacted Tickets",
    )
    knowledge_article_ids = fields.Many2many(
        "document.page",
        "helpdesk_release_note_document_page_rel",
        "release_note_id",
        "page_id",
        string="Knowledge Articles",
        domain="[('type', '=', 'content'), ('is_helpdesk_article', '=', True)]",
    )
    communication_log_ids = fields.One2many(
        "helpdesk.communication.log",
        "release_note_id",
        string="Customer Communication Logs",
    )
    problem_count = fields.Integer(compute="_compute_counts")
    ticket_count = fields.Integer(compute="_compute_counts")
    knowledge_article_count = fields.Integer(compute="_compute_counts")
    communication_count = fields.Integer(compute="_compute_counts")
    open_ticket_count = fields.Integer(compute="_compute_counts")

    @api.depends(
        "problem_ids",
        "ticket_ids",
        "ticket_ids.stage_id",
        "knowledge_article_ids",
        "communication_log_ids",
    )
    def _compute_counts(self):
        for record in self:
            record.problem_count = len(record.problem_ids)
            record.ticket_count = len(record.ticket_ids)
            record.knowledge_article_count = len(record.knowledge_article_ids)
            record.communication_count = len(record.communication_log_ids)
            record.open_ticket_count = len(record.ticket_ids.filtered(lambda ticket: not ticket.closed))

    @api.onchange("problem_ids")
    def _onchange_problem_ids(self):
        for record in self:
            ticket_ids = record.ticket_ids.ids
            article_ids = record.knowledge_article_ids.ids
            for problem in record.problem_ids:
                ticket_ids.extend(problem.ticket_ids.ids)
                if problem.knowledge_article_id:
                    article_ids.append(problem.knowledge_article_id.id)
            record.ticket_ids = [(6, 0, list(dict.fromkeys(ticket_ids)))]
            record.knowledge_article_ids = [(6, 0, list(dict.fromkeys(article_ids)))]
            if not record.team_id and record.problem_ids[:1].team_id:
                record.team_id = record.problem_ids[:1].team_id

    def action_mark_planned(self):
        self.write({"state": "planned"})
        return True

    def action_mark_in_progress(self):
        self.write({"state": "in_progress"})
        return True

    def action_mark_rolled_out(self):
        values = {"state": "rolled_out"}
        if not self.release_date:
            values["release_date"] = fields.Date.context_today(self)
        self.write(values)
        return True

    def action_mark_communicated(self):
        self.write({"state": "communicated"})
        return True

    def action_close(self):
        self.write({"state": "closed"})
        return True

    def action_open_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_mgmt.helpdesk_ticket_action")
        action["domain"] = [("id", "in", self.ticket_ids.ids)]
        action["context"] = {"search_default_open": 0}
        return action

    def action_open_problems(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_problem_management.action_helpdesk_problem"
        )
        action["domain"] = [("id", "in", self.problem_ids.ids)]
        return action

    def action_open_knowledge_articles(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_knowledge.action_helpdesk_knowledge_articles"
        )
        action["domain"] = [("id", "in", self.knowledge_article_ids.ids)]
        return action

    def action_open_communication_logs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_customer_communication_log.action_helpdesk_communication_log"
        )
        action["domain"] = [("release_note_id", "=", self.id)]
        action["context"] = {"default_release_note_id": self.id}
        return action

    def action_log_customer_update(self):
        for record in self:
            if not record.ticket_ids:
                raise UserError(_("Add at least one impacted ticket before logging a customer update."))
            if not record.customer_message:
                raise UserError(_("Customer message is required before logging a release communication."))
            for ticket in record.ticket_ids:
                ticket._create_communication_log(
                    channel="manual",
                    direction="outbound",
                    communication_type="status_change",
                    status="done",
                    subject=record.name,
                    summary=record.summary,
                    body=record.customer_message,
                    partner=ticket.partner_id,
                    user=record.owner_id,
                    source_model=record._name,
                    source_res_id=record.id,
                    release_note=record,
                )
            if record.state == "rolled_out":
                record.state = "communicated"
        return True

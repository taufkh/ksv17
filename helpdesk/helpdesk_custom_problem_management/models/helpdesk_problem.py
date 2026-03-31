from odoo import _, api, fields, models


class HelpdeskProblem(models.Model):
    _name = "helpdesk.problem"
    _description = "Helpdesk Problem"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "severity desc, detected_date desc, id desc"

    state_selection = [
        ("draft", "Draft"),
        ("investigating", "Investigating"),
        ("known_error", "Known Error"),
        ("monitoring", "Monitoring"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
    ]
    severity_selection = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    name = fields.Char(required=True, tracking=True)
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="draft",
        tracking=True,
    )
    severity = fields.Selection(
        selection=severity_selection,
        required=True,
        default="medium",
        tracking=True,
    )
    known_error = fields.Boolean(tracking=True)
    detected_date = fields.Date(default=fields.Date.context_today, tracking=True)
    next_review_date = fields.Date(tracking=True)
    partner_id = fields.Many2one("res.partner", string="Customer", tracking=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Helpdesk Team", tracking=True)
    support_asset_id = fields.Many2one(
        "helpdesk.support.asset",
        string="Support Asset",
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
    )
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    problem_owner_id = fields.Many2one(
        "res.users",
        string="Problem Owner",
        default=lambda self: self.env.user,
        tracking=True,
        domain=[("share", "=", False)],
    )
    knowledge_article_id = fields.Many2one(
        "document.page",
        string="Knowledge Article",
        domain="[('type', '=', 'content'), ('is_helpdesk_article', '=', True)]",
        tracking=True,
    )
    impact_summary = fields.Text()
    root_cause_summary = fields.Text()
    workaround = fields.Html()
    permanent_fix_plan = fields.Html()
    resolution_summary = fields.Html()
    ticket_ids = fields.One2many("helpdesk.ticket", "problem_id", string="Tickets")
    ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    open_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    escalated_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    overdue_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    last_ticket_update = fields.Datetime(compute="_compute_metrics", store=True)

    @api.depends(
        "ticket_ids",
        "ticket_ids.closed",
        "ticket_ids.escalated",
        "ticket_ids.sla_deadline",
        "ticket_ids.write_date",
    )
    def _compute_metrics(self):
        now = fields.Datetime.now()
        for problem in self:
            tickets = problem.ticket_ids
            problem.ticket_count = len(tickets)
            problem.open_ticket_count = len(tickets.filtered(lambda ticket: not ticket.closed))
            problem.escalated_ticket_count = len(tickets.filtered("escalated"))
            problem.overdue_ticket_count = len(
                tickets.filtered(
                    lambda ticket: not ticket.closed
                    and ticket.sla_deadline
                    and ticket.sla_deadline < now
                )
            )
            problem.last_ticket_update = max(tickets.mapped("write_date")) if tickets else False

    @api.onchange("known_error")
    def _onchange_known_error(self):
        for problem in self:
            if problem.known_error and problem.state in {"draft", "investigating"}:
                problem.state = "known_error"

    def action_start_investigation(self):
        self.write({"state": "investigating"})
        return True

    def action_mark_known_error(self):
        self.write({"state": "known_error", "known_error": True})
        return True

    def action_mark_monitoring(self):
        self.write({"state": "monitoring"})
        return True

    def action_mark_resolved(self):
        self.write({"state": "resolved"})
        return True

    def action_close(self):
        self.write({"state": "closed"})
        return True

    def action_open_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_mgmt.helpdesk_ticket_action")
        action["domain"] = [("problem_id", "=", self.id)]
        action["context"] = {"search_default_open": 0}
        return action

    def action_open_knowledge_article(self):
        self.ensure_one()
        if not self.knowledge_article_id:
            return False
        return self.knowledge_article_id.get_formview_action()

    def action_create_knowledge_article(self):
        self.ensure_one()
        form_view = self.env.ref("document_page.view_wiki_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Knowledge Article"),
            "res_model": "document.page",
            "view_mode": "form",
            "views": [(form_view.id, "form")],
            "target": "current",
            "context": {
                "default_name": _("%(problem)s - Known Issue Guide") % {"problem": self.name},
                "default_type": "content",
                "default_draft_name": "1.0",
                "default_is_helpdesk_article": True,
                "default_article_status": "draft",
                "default_article_owner_id": self.problem_owner_id.id or self.env.user.id,
                "default_helpdesk_primary_ticket_id": self.ticket_ids[:1].id,
                "default_helpdesk_ticket_ids": [(6, 0, self.ticket_ids.ids)],
                "default_content": (
                    "<h2>Problem Summary</h2><p>%s</p>"
                    "<h2>Impact</h2><p>%s</p>"
                    "<h2>Workaround</h2><p>Document the current safe workaround here.</p>"
                    "<h2>Permanent Fix</h2><p>Document the permanent remediation plan here.</p>"
                )
                % (self.name, self.impact_summary or ""),
            },
        }

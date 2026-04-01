from odoo import _, api, fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    is_helpdesk_article = fields.Boolean(index=True)
    article_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("internal", "Internal"),
            ("portal_ready", "Portal Ready"),
            ("obsolete", "Obsolete"),
        ],
        default="draft",
        tracking=True,
    )
    resolution_pattern = fields.Selection(
        [
            ("workaround", "Workaround"),
            ("fix", "Confirmed Fix"),
            ("configuration", "Configuration"),
            ("process", "Process Guidance"),
            ("faq", "FAQ"),
        ],
        tracking=True,
    )
    article_owner_id = fields.Many2one(
        "res.users",
        string="Article Owner",
        default=lambda self: self.env.user,
        tracking=True,
    )
    review_due_date = fields.Date(tracking=True)
    validated_on = fields.Datetime(readonly=True, tracking=True)
    validated_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    helpdesk_primary_ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Source Ticket",
        tracking=True,
    )
    helpdesk_ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_ticket_document_page_rel",
        "page_id",
        "ticket_id",
        string="Related Tickets",
    )
    helpdesk_ticket_count = fields.Integer(compute="_compute_helpdesk_ticket_count")
    helpdesk_team_id = fields.Many2one(
        related="helpdesk_primary_ticket_id.team_id",
        store=True,
        readonly=True,
        string="Helpdesk Team",
    )
    helpdesk_category_id = fields.Many2one(
        related="helpdesk_primary_ticket_id.category_id",
        store=True,
        readonly=True,
        string="Ticket Category",
    )
    helpdesk_type_id = fields.Many2one(
        related="helpdesk_primary_ticket_id.type_id",
        store=True,
        readonly=True,
        string="Ticket Type",
    )

    @api.depends("helpdesk_ticket_ids")
    def _compute_helpdesk_ticket_count(self):
        for page in self:
            page.helpdesk_ticket_count = len(page.helpdesk_ticket_ids)

    def action_mark_internal(self):
        self.write({"article_status": "internal"})
        return True

    def action_mark_portal_ready(self):
        self.write(
            {
                "article_status": "portal_ready",
                "validated_on": fields.Datetime.now(),
                "validated_by_id": self.env.user.id,
            }
        )
        return True

    def action_mark_obsolete(self):
        self.write({"article_status": "obsolete"})
        return True

    def action_mark_validated(self):
        self.write(
            {
                "validated_on": fields.Datetime.now(),
                "validated_by_id": self.env.user.id,
                "article_status": "internal"
                if self.article_status == "draft"
                else self.article_status,
            }
        )
        return True

    def action_open_related_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_mgmt.helpdesk_ticket_action"
        )
        action["domain"] = [("id", "in", self.helpdesk_ticket_ids.ids)]
        action["context"] = {"search_default_open": 0}
        return action

    def copy(self, default=None):
        default = dict(
            default or {},
            is_helpdesk_article=self.is_helpdesk_article,
            article_status="draft",
            helpdesk_primary_ticket_id=self.helpdesk_primary_ticket_id.id,
            helpdesk_ticket_ids=[(6, 0, self.helpdesk_ticket_ids.ids)],
        )
        return super().copy(default=default)


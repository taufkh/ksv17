from odoo import _, api, fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    portal_publication_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("review", "In Review"),
            ("approved", "Approved"),
            ("published", "Published"),
            ("retired", "Retired"),
        ],
        default="draft",
        tracking=True,
    )
    portal_visibility = fields.Selection(
        [
            ("all_customers", "All Customers"),
            ("contract_customers", "Contract Customers"),
            ("selected_customers", "Selected Customers"),
        ],
        default="all_customers",
        tracking=True,
    )
    portal_partner_ids = fields.Many2many(
        "res.partner",
        "document_page_portal_partner_rel",
        "page_id",
        "partner_id",
        string="Allowed Customers",
    )
    portal_contract_ids = fields.Many2many(
        "helpdesk.support.contract",
        "document_page_portal_contract_rel",
        "page_id",
        "contract_id",
        string="Allowed Support Contracts",
    )
    portal_summary = fields.Text(tracking=True)
    portal_keywords = fields.Char(tracking=True)
    portal_reviewed_on = fields.Datetime(readonly=True, tracking=True)
    portal_reviewed_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    portal_approved_on = fields.Datetime(readonly=True, tracking=True)
    portal_approved_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    portal_published_on = fields.Datetime(readonly=True, tracking=True)
    portal_published_by_id = fields.Many2one("res.users", readonly=True, tracking=True)
    portal_view_count = fields.Integer(default=0, tracking=True)
    portal_helpful_count = fields.Integer(default=0, tracking=True)
    portal_not_helpful_count = fields.Integer(default=0, tracking=True)
    portal_deflection_count = fields.Integer(default=0, tracking=True)
    portal_last_feedback_on = fields.Datetime(readonly=True, tracking=True)
    portal_feedback_score = fields.Float(
        compute="_compute_portal_feedback_score",
        store=True,
    )

    @api.depends("portal_helpful_count", "portal_not_helpful_count")
    def _compute_portal_feedback_score(self):
        for page in self:
            total = page.portal_helpful_count + page.portal_not_helpful_count
            page.portal_feedback_score = round((page.portal_helpful_count / total) * 100, 2) if total else 0.0

    def action_submit_portal_review(self):
        self.write({"portal_publication_state": "review"})
        return True

    def action_approve_portal_publication(self):
        self.write(
            {
                "portal_publication_state": "approved",
                "portal_reviewed_on": fields.Datetime.now(),
                "portal_reviewed_by_id": self.env.user.id,
                "portal_approved_on": fields.Datetime.now(),
                "portal_approved_by_id": self.env.user.id,
            }
        )
        return True

    def action_publish_to_portal(self):
        self.write(
            {
                "portal_publication_state": "published",
                "portal_published_on": fields.Datetime.now(),
                "portal_published_by_id": self.env.user.id,
                "article_status": "portal_ready" if self.article_status != "obsolete" else self.article_status,
            }
        )
        return True

    def action_retire_from_portal(self):
        self.write({"portal_publication_state": "retired"})
        return True

    def _is_visible_for_portal(self, partner=False, contract=False, team=False):
        self.ensure_one()
        if not self.active or not self.is_helpdesk_article or self.portal_publication_state != "published":
            return False
        root_partner = (partner.commercial_partner_id if partner else False) or partner
        if self.portal_visibility == "selected_customers":
            allowed_roots = self.portal_partner_ids.mapped("commercial_partner_id") or self.portal_partner_ids
            if root_partner not in allowed_roots:
                return False
        elif self.portal_visibility == "contract_customers":
            contract_set = contract
            if not contract_set and root_partner:
                contract_set = self.env["helpdesk.support.contract"].sudo().search(
                    [
                        ("partner_id", "=", root_partner.id),
                        ("state", "in", ["active", "expiring"]),
                    ]
                )
            if not contract_set or not (contract_set & self.portal_contract_ids):
                return False
        if team and self.helpdesk_team_id and team != self.helpdesk_team_id:
            return False
        return True

    def _get_ticket_relevance_score(self, ticket):
        self.ensure_one()
        score = 0
        if self.helpdesk_team_id and ticket.team_id == self.helpdesk_team_id:
            score += 3
        if self.helpdesk_category_id and ticket.category_id == self.helpdesk_category_id:
            score += 3
        if self.helpdesk_type_id and ticket.type_id == self.helpdesk_type_id:
            score += 2
        if ticket.support_contract_id and ticket.support_contract_id in self.portal_contract_ids:
            score += 2
        if self.helpdesk_primary_ticket_id == ticket:
            score += 2
        return score

    def _register_portal_view(self):
        self.sudo().write({"portal_view_count": self.portal_view_count + 1})

    def _register_portal_feedback(self, helpful):
        values = {"portal_last_feedback_on": fields.Datetime.now()}
        if helpful:
            values["portal_helpful_count"] = self.portal_helpful_count + 1
        else:
            values["portal_not_helpful_count"] = self.portal_not_helpful_count + 1
        self.sudo().write(values)

    def _register_portal_deflection(self):
        self.sudo().write({"portal_deflection_count": self.portal_deflection_count + 1})

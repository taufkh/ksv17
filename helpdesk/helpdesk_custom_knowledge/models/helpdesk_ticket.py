from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    knowledge_article_ids = fields.Many2many(
        "document.page",
        "helpdesk_ticket_document_page_rel",
        "ticket_id",
        "page_id",
        string="Knowledge Articles",
        domain="[('type', '=', 'content'), ('is_helpdesk_article', '=', True)]",
    )
    knowledge_article_count = fields.Integer(compute="_compute_knowledge_article_count")

    @api.depends("knowledge_article_ids")
    def _compute_knowledge_article_count(self):
        for ticket in self:
            ticket.knowledge_article_count = len(ticket.knowledge_article_ids)

    def _default_knowledge_category(self):
        self.ensure_one()
        company_domain = [("company_id", "in", [False, self.company_id.id])]
        return self.env["document.page"].search(
            [("is_helpdesk_article", "=", True), ("type", "=", "category"), ("parent_id", "=", False)]
            + company_domain,
            limit=1,
        )

    def _default_knowledge_content(self):
        self.ensure_one()
        return """
            <h2>Issue Summary</h2>
            <p>%s</p>
            <h2>Symptoms</h2>
            <p>Describe the exact error, business impact, and trigger condition.</p>
            <h2>Root Cause</h2>
            <p>Document the confirmed or suspected root cause.</p>
            <h2>Resolution Steps</h2>
            <ol>
                <li>Step 1</li>
                <li>Step 2</li>
                <li>Step 3</li>
            </ol>
            <h2>Escalation Notes</h2>
            <p>Document when this should be escalated and to whom.</p>
        """ % (self.description or self.name)

    def action_open_knowledge_articles(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_knowledge.action_helpdesk_knowledge_articles"
        )
        action["domain"] = [("id", "in", self.knowledge_article_ids.ids)]
        action["context"] = {"default_helpdesk_ticket_ids": [(6, 0, [self.id])]}
        return action

    def action_create_knowledge_article(self):
        self.ensure_one()
        form_view = self.env.ref("document_page.view_wiki_form")
        category = self._default_knowledge_category()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Knowledge Article"),
            "res_model": "document.page",
            "view_mode": "form",
            "views": [(form_view.id, "form")],
            "target": "current",
            "context": {
                "default_name": _("%(ticket)s - Resolution Guide") % {"ticket": self.number},
                "default_type": "content",
                "default_parent_id": category.id if category else False,
                "default_draft_name": "1.0",
                "default_draft_summary": _("Created from helpdesk ticket %(ticket)s") % {"ticket": self.number},
                "default_content": self._default_knowledge_content(),
                "default_is_helpdesk_article": True,
                "default_article_status": "draft",
                "default_article_owner_id": self.user_id.id or self.env.user.id,
                "default_helpdesk_primary_ticket_id": self.id,
                "default_helpdesk_ticket_ids": [(6, 0, [self.id])],
            },
        }


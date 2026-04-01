from odoo import fields, models


class DocumentPage(models.Model):
    _inherit = "document.page"

    release_note_ids = fields.Many2many(
        "helpdesk.release.note",
        "helpdesk_release_note_document_page_rel",
        "page_id",
        "release_note_id",
        string="Release Notes",
    )
    release_note_count = fields.Integer(compute="_compute_release_note_count")

    def _compute_release_note_count(self):
        for page in self:
            page.release_note_count = len(page.release_note_ids)

    def action_open_release_notes(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_release_note_tracking.action_helpdesk_release_note"
        )
        action["domain"] = [("id", "in", self.release_note_ids.ids)]
        action["context"] = {"default_knowledge_article_ids": [(6, 0, [self.id])]}
        return action

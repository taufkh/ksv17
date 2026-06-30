from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    image_attachment_ids = fields.One2many(
        "account.move.attachment.image",
        "move_id",
        string="Lampiran",
        copy=True,
    )

    def _get_image_attachment_sections(self):
        self.ensure_one()
        sections = []
        attachments = self.image_attachment_ids.sorted(lambda rec: (rec.sequence, rec.id))
        general_attachments = attachments.filtered(lambda rec: not rec.move_line_id)
        if general_attachments:
            sections.append(
                {
                    "key": "general",
                    "title": _("Lampiran Umum"),
                    "attachments": general_attachments,
                }
            )

        invoice_lines = self.invoice_line_ids.sorted(lambda rec: (rec.sequence, rec.id))
        for line in invoice_lines:
            line_attachments = attachments.filtered(lambda rec: rec.move_line_id == line)
            if not line_attachments:
                continue
            sections.append(
                {
                    "key": f"line_{line.id}",
                    "title": line.product_id.display_name or line.name,
                    "attachments": line_attachments,
                }
            )
        return sections

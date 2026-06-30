from odoo import _, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    image_attachment_ids = fields.One2many(
        "sale.order.attachment.image",
        "sale_order_id",
        string="Lampiran",
        copy=True,
    )

    def _get_image_attachment_sections(self):
        self.ensure_one()
        sections = []
        attachments = self.image_attachment_ids.sorted(lambda rec: (rec.sequence, rec.id))
        general_attachments = attachments.filtered(lambda rec: not rec.sale_order_line_id)
        if general_attachments:
            sections.append(
                {
                    "key": "general",
                    "title": _("Lampiran Umum"),
                    "attachments": general_attachments,
                }
            )

        for line in self.order_line.sorted(lambda rec: (rec.sequence, rec.id)):
            line_attachments = attachments.filtered(lambda rec: rec.sale_order_line_id == line)
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

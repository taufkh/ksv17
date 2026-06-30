import base64
import io

from PIL import Image

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMoveAttachmentImage(models.Model):
    _name = "account.move.attachment.image"
    _description = "Invoice Attachment Image"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    move_id = fields.Many2one(
        "account.move",
        string="Invoice",
        required=True,
        ondelete="cascade",
        index=True,
    )
    move_line_id = fields.Many2one(
        "account.move.line",
        string="Referensi Item",
        ondelete="set null",
    )
    name = fields.Char(string="Judul")
    description = fields.Text(string="Keterangan")
    image = fields.Image(string="Gambar", required=True, max_width=1920, max_height=1920)
    image_width = fields.Integer(
        string="Lebar Gambar",
        compute="_compute_image_metadata",
        store=True,
    )
    image_height = fields.Integer(
        string="Tinggi Gambar",
        compute="_compute_image_metadata",
        store=True,
    )
    report_layout = fields.Selection(
        [
            ("full", "Full Width"),
            ("half", "Half Width"),
        ],
        string="Layout Report",
        compute="_compute_image_metadata",
        store=True,
    )
    item_reference = fields.Char(
        string="Referensi Item",
        compute="_compute_item_reference",
        store=True,
    )

    @api.depends("move_line_id.product_id", "move_line_id.name")
    def _compute_item_reference(self):
        for attachment in self:
            line = attachment.move_line_id
            attachment.item_reference = (
                line.product_id.display_name or line.name or False
            )

    @api.depends("image")
    def _compute_image_metadata(self):
        for attachment in self:
            width = 0
            height = 0
            layout = "half"
            if attachment.image:
                try:
                    image_bytes = base64.b64decode(attachment.image)
                    with Image.open(io.BytesIO(image_bytes)) as image:
                        width, height = image.size
                except Exception:
                    width = 0
                    height = 0
                if width and height and (width / float(height)) >= 1.35:
                    layout = "full"
            attachment.image_width = width
            attachment.image_height = height
            attachment.report_layout = layout

    @api.constrains("move_id", "move_line_id")
    def _check_move_line(self):
        for attachment in self:
            if attachment.move_line_id and attachment.move_line_id.move_id != attachment.move_id:
                raise ValidationError(
                    _("Referensi item invoice harus berasal dari invoice yang sama.")
                )

    @api.onchange("move_line_id")
    def _onchange_move_line_id(self):
        for attachment in self:
            if attachment.move_line_id and not attachment.name:
                attachment.name = (
                    attachment.move_line_id.product_id.display_name
                    or attachment.move_line_id.name
                )

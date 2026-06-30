from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    auto_scrap_on_pos_closing = fields.Boolean(
        string="Scrap Unsold at POS Closing",
        help=(
            "Automatically scrap any remaining stock for this product from the POS "
            "source location when the POS session closes."
        ),
    )

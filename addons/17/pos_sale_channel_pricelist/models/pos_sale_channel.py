from odoo import fields, models


class PosSaleChannel(models.Model):
    _inherit = "pos.sale.channel"

    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
        help="Orders using this sales channel will use this pricelist in POS.",
        ondelete="set null",
    )

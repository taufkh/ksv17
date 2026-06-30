from odoo import fields, models


class PosSaleChannel(models.Model):
    _inherit = "pos.sale.channel"

    channel_tax_id = fields.Many2one(
        "account.tax",
        string="Channel Tax",
        domain=[("type_tax_use", "=", "sale")],
        help="Orders using this sales channel will apply this sales tax in POS.",
    )
    fiscal_position_id = fields.Many2one(
        "account.tax",
        string="Legacy Channel Tax",
        related="channel_tax_id",
        readonly=False,
        help="Compatibility alias for previous channel tax field.",
    )

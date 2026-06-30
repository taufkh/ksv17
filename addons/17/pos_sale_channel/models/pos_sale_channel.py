from odoo import fields, models


class PosSaleChannel(models.Model):
    _name = "pos.sale.channel"
    _description = "POS Sale Channel"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", string="Company")
    channel_type = fields.Selection(
        [
            ("other", "Other"),
            ("dine_in", "Dine In"),
            ("takeaway", "Takeaway"),
        ],
        string="Channel Type",
        default="other",
        required=True,
    )

    _sql_constraints = [
        ("pos_sale_channel_name_company_uniq", "unique(name, company_id)", "Channel name must be unique per company."),
    ]

from odoo import fields, models


class MembershipPointLedger(models.Model):
    _name = "membership.point.ledger"
    _description = "Membership Point Ledger"
    _order = "date desc, id desc"

    partner_id = fields.Many2one("res.partner", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    date = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    points = fields.Integer(required=True)
    direction = fields.Selection(
        [("earned", "Earned"), ("redeemed", "Redeemed"), ("adjustment", "Adjustment")],
        required=True,
        default="earned",
    )
    source = fields.Selection(
        [
            ("pos_order", "POS Order"),
            ("reward", "Reward"),
            ("manual", "Manual"),
            ("reversal", "Reversal"),
        ],
        required=True,
        default="manual",
    )
    pos_order_id = fields.Many2one("pos.order", index=True, ondelete="set null")
    reference = fields.Char()

    _sql_constraints = [
        (
            "membership_point_value_positive",
            "CHECK(points >= 0)",
            "Point ledger value must be positive.",
        ),
    ]

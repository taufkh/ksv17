from odoo import fields, models


class MembershipDepositLedger(models.Model):
    _name = "membership.deposit.ledger"
    _description = "Membership Deposit Ledger"
    _order = "date desc, id desc"

    partner_id = fields.Many2one("res.partner", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    date = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    amount = fields.Monetary(required=True, currency_field="currency_id")
    direction = fields.Selection(
        [("in", "In"), ("out", "Out")],
        required=True,
        default="in",
    )
    source = fields.Selection(
        [
            ("topup", "Top Up"),
            ("usage", "POS Usage"),
            ("refund", "Refund"),
            ("adjustment", "Adjustment"),
            ("reversal", "Reversal"),
        ],
        required=True,
        default="adjustment",
    )
    pos_order_id = fields.Many2one("pos.order", index=True, ondelete="set null")
    pos_payment_id = fields.Many2one("pos.payment", index=True, ondelete="set null")
    reference = fields.Char()
    state = fields.Selection(
        [("draft", "Draft"), ("posted", "Posted"), ("cancelled", "Cancelled")],
        required=True,
        default="posted",
    )

    _sql_constraints = [
        (
            "membership_deposit_amount_positive",
            "CHECK(amount >= 0)",
            "Deposit ledger amount must be positive.",
        ),
    ]

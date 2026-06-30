from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_membership_deposit = fields.Boolean(
        string="Membership Deposit Method",
        help="Use this payment method to spend a member's deposit wallet in POS.",
    )

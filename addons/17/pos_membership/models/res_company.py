from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    membership_barcode_prefix = fields.Char(
        string="Membership Barcode Prefix",
        default="MBR",
    )
    membership_point_spend_amount = fields.Monetary(
        string="Amount per Point",
        currency_field="currency_id",
        default=10000.0,
        help="Customer earns the configured point value every time the eligible amount reaches this threshold.",
    )
    membership_point_value = fields.Integer(
        string="Points Earned",
        default=1,
    )
    membership_topup_product_id = fields.Many2one(
        "product.product",
        string="Top Up Product",
        domain=[("available_in_pos", "=", True)],
    )
    membership_deposit_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Deposit Payment Method",
        domain=[("is_membership_deposit", "=", True)],
    )
    membership_auto_load_members = fields.Boolean(
        string="Load Members in POS",
        default=True,
        help="If enabled, membership fields are included in partner data loaded by POS sessions.",
    )

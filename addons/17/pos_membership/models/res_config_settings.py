from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    membership_barcode_prefix = fields.Char(
        related="company_id.membership_barcode_prefix",
        readonly=False,
    )
    membership_point_spend_amount = fields.Monetary(
        related="company_id.membership_point_spend_amount",
        readonly=False,
    )
    membership_point_value = fields.Integer(
        related="company_id.membership_point_value",
        readonly=False,
    )
    membership_topup_product_id = fields.Many2one(
        related="company_id.membership_topup_product_id",
        readonly=False,
    )
    membership_deposit_payment_method_id = fields.Many2one(
        related="company_id.membership_deposit_payment_method_id",
        readonly=False,
    )
    membership_auto_load_members = fields.Boolean(
        related="company_id.membership_auto_load_members",
        readonly=False,
    )

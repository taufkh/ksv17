from odoo import fields, models


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    membership_only = fields.Boolean(
        string="Member Only (POS)",
        help=(
            "If enabled, this POS discount/promo only applies when the selected "
            "customer is a registered membership customer."
        ),
    )

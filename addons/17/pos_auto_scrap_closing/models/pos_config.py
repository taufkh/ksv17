from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    auto_scrap_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Accounting Currency",
        readonly=True,
    )
    auto_scrap_unsold_products = fields.Boolean(
        string="Auto Scrap Unsold Daily Products",
        help=(
            "When enabled, products flagged to be scrapped at POS closing will be "
            "automatically scrapped from the POS source location when the session closes."
        ),
    )
    auto_scrap_require_manager_approval = fields.Boolean(
        string="Require Manager Approval Above Loss Limit",
        help=(
            "If enabled, a non-manager cannot close the POS session when the projected "
            "auto scrap loss exceeds the configured threshold."
        ),
    )
    auto_scrap_loss_limit = fields.Monetary(
        string="Auto Scrap Loss Limit",
        currency_field="auto_scrap_currency_id",
        help=(
            "Projected loss threshold for auto scrap. Leave at 0.00 to disable the "
            "approval threshold."
        ),
    )

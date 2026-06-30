from odoo import fields, models


class DailyClaimLog(models.Model):
    _name = "daily.claim.log"
    _description = "Daily Membership Claim Log"
    _order = "date desc, id desc"

    partner_id = fields.Many2one("res.partner", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    product_id = fields.Many2one("product.product", required=True, ondelete="restrict")
    pos_order_id = fields.Many2one("pos.order", index=True, ondelete="set null")

    _sql_constraints = [
        (
            "daily_claim_log_partner_date_company_uniq",
            "unique(partner_id, date, company_id)",
            "Daily reward hanya dapat diklaim 1 kali per hari.",
        ),
    ]

from odoo import api, fields, models


class HelpdeskContractRenewal(models.Model):
    _inherit = "helpdesk.contract.renewal"

    weighted_revenue = fields.Monetary(
        compute="_compute_analytics_metrics",
        currency_field="currency_id",
        store=True,
    )
    revenue_at_risk = fields.Monetary(
        compute="_compute_analytics_metrics",
        currency_field="currency_id",
        store=True,
    )
    follow_up_overdue = fields.Boolean(
        compute="_compute_analytics_metrics",
        store=True,
    )
    follow_up_overdue_days = fields.Integer(
        compute="_compute_analytics_metrics",
        store=True,
    )
    expiry_bucket = fields.Selection(
        [
            ("expired", "Expired"),
            ("0_7", "0-7 Days"),
            ("8_14", "8-14 Days"),
            ("15_30", "15-30 Days"),
            ("30_plus", "30+ Days"),
            ("unknown", "No End Date"),
        ],
        compute="_compute_analytics_metrics",
        store=True,
    )
    probability_bucket = fields.Selection(
        [
            ("0_24", "0-24%"),
            ("25_49", "25-49%"),
            ("50_74", "50-74%"),
            ("75_100", "75-100%"),
        ],
        compute="_compute_analytics_metrics",
        store=True,
    )

    @api.depends("expected_revenue", "renewal_probability", "state", "risk_level", "next_follow_up_date", "days_to_expiry")
    def _compute_analytics_metrics(self):
        today = fields.Date.today()
        active_states = {"open", "in_review", "handoff_sent"}
        for renewal in self:
            expected = renewal.expected_revenue or 0.0
            probability = renewal.renewal_probability or 0
            renewal.weighted_revenue = expected * probability / 100.0
            renewal.follow_up_overdue = bool(
                renewal.state in active_states
                and renewal.next_follow_up_date
                and renewal.next_follow_up_date < today
            )
            renewal.follow_up_overdue_days = (
                (today - renewal.next_follow_up_date).days if renewal.follow_up_overdue else 0
            )
            renewal.revenue_at_risk = (
                expected
                if renewal.state in active_states
                and (
                    renewal.risk_level in {"high", "critical"}
                    or renewal.follow_up_overdue
                )
                else 0.0
            )
            if renewal.end_date:
                if renewal.days_to_expiry < 0:
                    renewal.expiry_bucket = "expired"
                elif renewal.days_to_expiry <= 7:
                    renewal.expiry_bucket = "0_7"
                elif renewal.days_to_expiry <= 14:
                    renewal.expiry_bucket = "8_14"
                elif renewal.days_to_expiry <= 30:
                    renewal.expiry_bucket = "15_30"
                else:
                    renewal.expiry_bucket = "30_plus"
            else:
                renewal.expiry_bucket = "unknown"

            if probability < 25:
                renewal.probability_bucket = "0_24"
            elif probability < 50:
                renewal.probability_bucket = "25_49"
            elif probability < 75:
                renewal.probability_bucket = "50_74"
            else:
                renewal.probability_bucket = "75_100"

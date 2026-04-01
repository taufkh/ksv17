from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    helpdesk_360_renewal_overdue_followup_count = fields.Integer(
        string="Overdue Renewal Follow-ups",
        compute="_compute_helpdesk_renewal_analytics_360",
        compute_sudo=True,
    )
    helpdesk_360_renewal_weighted_revenue = fields.Monetary(
        string="Weighted Renewal Revenue",
        currency_field="currency_id",
        compute="_compute_helpdesk_renewal_analytics_360",
        compute_sudo=True,
    )
    helpdesk_360_renewal_risk_segment = fields.Selection(
        [
            ("stable", "Stable"),
            ("watch", "Watch"),
            ("at_risk", "At Risk"),
            ("critical", "Critical"),
        ],
        string="Renewal Risk Segment",
        compute="_compute_helpdesk_renewal_analytics_360",
        compute_sudo=True,
    )

    def _compute_helpdesk_renewal_analytics_360(self):
        for partner in self:
            renewals = partner.helpdesk_360_renewal_ids
            active = renewals.filtered(lambda renewal: renewal.state in {"open", "in_review", "handoff_sent"})
            overdue = active.filtered("follow_up_overdue")
            critical = active.filtered(lambda renewal: renewal.risk_level == "critical")
            at_risk = active.filtered(lambda renewal: renewal.risk_level in {"high", "critical"})
            partner.helpdesk_360_renewal_overdue_followup_count = len(overdue)
            partner.helpdesk_360_renewal_weighted_revenue = sum(active.mapped("weighted_revenue"))
            if critical or overdue:
                partner.helpdesk_360_renewal_risk_segment = "critical"
            elif at_risk:
                partner.helpdesk_360_renewal_risk_segment = "at_risk"
            elif active:
                partner.helpdesk_360_renewal_risk_segment = "watch"
            else:
                partner.helpdesk_360_renewal_risk_segment = "stable"

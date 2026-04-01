from odoo import fields, models, tools


class HelpdeskContractRenewalAnalyticsReport(models.Model):
    _name = "helpdesk.contract.renewal.analytics.report"
    _description = "Helpdesk Contract Renewal Analytics Report"
    _auto = False
    _order = "follow_up_overdue desc, next_follow_up_date asc, expected_revenue desc"

    renewal_id = fields.Many2one("helpdesk.contract.renewal", readonly=True)
    contract_id = fields.Many2one("helpdesk.support.contract", readonly=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", readonly=True)
    sales_user_id = fields.Many2one("res.users", readonly=True)
    owner_id = fields.Many2one("res.users", readonly=True)
    contract_type = fields.Char(readonly=True)
    trigger_type = fields.Char(readonly=True)
    state = fields.Char(readonly=True)
    risk_level = fields.Char(readonly=True)
    probability_bucket = fields.Char(readonly=True)
    expiry_bucket = fields.Char(readonly=True)
    days_to_expiry = fields.Integer(readonly=True)
    next_follow_up_date = fields.Date(readonly=True)
    follow_up_overdue = fields.Boolean(readonly=True)
    follow_up_overdue_days = fields.Integer(readonly=True)
    renewal_probability = fields.Integer(readonly=True)
    expected_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    weighted_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    revenue_at_risk = fields.Monetary(currency_field="currency_id", readonly=True)
    won_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    lost_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    active_pipeline_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    count_renewals = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    renewal.id AS id,
                    renewal.id AS renewal_id,
                    renewal.contract_id,
                    renewal.partner_id,
                    renewal.company_id,
                    company.currency_id,
                    renewal.team_id,
                    renewal.sales_user_id,
                    renewal.owner_id,
                    renewal.contract_type,
                    renewal.trigger_type,
                    renewal.state,
                    renewal.risk_level,
                    renewal.probability_bucket,
                    renewal.expiry_bucket,
                    renewal.days_to_expiry,
                    renewal.next_follow_up_date,
                    renewal.follow_up_overdue,
                    renewal.follow_up_overdue_days,
                    renewal.renewal_probability,
                    COALESCE(renewal.expected_revenue, 0.0) AS expected_revenue,
                    COALESCE(renewal.weighted_revenue, 0.0) AS weighted_revenue,
                    COALESCE(renewal.revenue_at_risk, 0.0) AS revenue_at_risk,
                    CASE WHEN renewal.state = 'won' THEN COALESCE(renewal.expected_revenue, 0.0) ELSE 0.0 END AS won_revenue,
                    CASE WHEN renewal.state = 'lost' THEN COALESCE(renewal.expected_revenue, 0.0) ELSE 0.0 END AS lost_revenue,
                    CASE
                        WHEN renewal.state IN ('open', 'in_review', 'handoff_sent')
                        THEN COALESCE(renewal.expected_revenue, 0.0)
                        ELSE 0.0
                    END AS active_pipeline_revenue,
                    1 AS count_renewals
                FROM helpdesk_contract_renewal renewal
                LEFT JOIN res_company company ON company.id = renewal.company_id
            )
            """
        )

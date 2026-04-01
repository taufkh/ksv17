from odoo import fields, models, tools


class HelpdeskRenewalForecastDashboard(models.Model):
    _name = "helpdesk.renewal.forecast.dashboard"
    _description = "Helpdesk Renewal Forecast Dashboard"
    _auto = False
    _order = "month_start desc, scope_sequence, name"

    scope_type = fields.Selection(
        [("overall", "Overall"), ("team", "Team"), ("sales_user", "Salesperson")],
        readonly=True,
    )
    scope_sequence = fields.Integer(readonly=True)
    name = fields.Char(readonly=True)
    month_start = fields.Date(readonly=True)
    month_label = fields.Char(readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", readonly=True)
    sales_user_id = fields.Many2one("res.users", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    target_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    budget_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    weighted_forecast_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    pipeline_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    won_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    lost_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    revenue_at_risk = fields.Monetary(currency_field="currency_id", readonly=True)
    overdue_follow_up_count = fields.Integer(readonly=True)
    open_watch_count = fields.Integer(readonly=True)
    gap_to_target = fields.Monetary(currency_field="currency_id", readonly=True)
    gap_to_budget = fields.Monetary(currency_field="currency_id", readonly=True)
    attainment_rate = fields.Float(readonly=True)
    budget_attainment_rate = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH renewal_base AS (
                    SELECT
                        DATE_TRUNC('month', COALESCE(renewal.end_date::timestamp, CURRENT_DATE::timestamp))::date AS month_start,
                        COALESCE(
                            renewal.company_id,
                            contract.company_id,
                            (SELECT id FROM res_company ORDER BY id LIMIT 1)
                        ) AS company_id,
                        company.currency_id,
                        renewal.team_id,
                        renewal.sales_user_id,
                        renewal.state,
                        COALESCE(renewal.expected_revenue, 0.0) AS expected_revenue,
                        COALESCE(renewal.weighted_revenue, 0.0) AS weighted_revenue,
                        COALESCE(renewal.revenue_at_risk, 0.0) AS revenue_at_risk,
                        COALESCE(renewal.follow_up_overdue, FALSE) AS follow_up_overdue
                    FROM helpdesk_contract_renewal renewal
                    LEFT JOIN helpdesk_support_contract contract ON contract.id = renewal.contract_id
                    LEFT JOIN res_company company ON company.id = COALESCE(
                        renewal.company_id,
                        contract.company_id,
                        (SELECT id FROM res_company ORDER BY id LIMIT 1)
                    )
                ),
                target_rows AS (
                    SELECT
                        target.month_start,
                        target.scope_type,
                        CASE target.scope_type
                            WHEN 'overall' THEN 1
                            WHEN 'team' THEN 2
                            ELSE 3
                        END AS scope_sequence,
                        CASE
                            WHEN target.scope_type = 'overall' THEN COALESCE(company.name, 'Company')
                            WHEN target.scope_type = 'team' THEN COALESCE(team.name, 'No Team')
                            ELSE COALESCE(user_partner.name, 'Unassigned Salesperson')
                        END AS name,
                        target.team_id,
                        target.sales_user_id,
                        target.company_id,
                        company.currency_id,
                        target.target_amount,
                        COALESCE(target.budget_amount, 0.0) AS budget_amount
                    FROM helpdesk_renewal_target target
                    LEFT JOIN res_company company ON company.id = target.company_id
                    LEFT JOIN helpdesk_ticket_team team ON team.id = target.team_id
                    LEFT JOIN res_users sales_user ON sales_user.id = target.sales_user_id
                    LEFT JOIN res_partner user_partner ON user_partner.id = sales_user.partner_id
                    WHERE target.active
                ),
                forecast_overall AS (
                    SELECT
                        month_start,
                        'overall'::varchar AS scope_type,
                        NULL::integer AS team_id,
                        NULL::integer AS sales_user_id,
                        company_id,
                        currency_id,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN weighted_revenue ELSE 0 END) AS weighted_forecast_amount,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN expected_revenue ELSE 0 END) AS pipeline_amount,
                        SUM(CASE WHEN state = 'won' THEN expected_revenue ELSE 0 END) AS won_amount,
                        SUM(CASE WHEN state = 'lost' THEN expected_revenue ELSE 0 END) AS lost_amount,
                        SUM(revenue_at_risk) AS revenue_at_risk,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') AND follow_up_overdue THEN 1 ELSE 0 END) AS overdue_follow_up_count,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END) AS open_watch_count
                    FROM renewal_base
                    GROUP BY month_start, company_id, currency_id
                ),
                forecast_team AS (
                    SELECT
                        month_start,
                        'team'::varchar AS scope_type,
                        team_id,
                        NULL::integer AS sales_user_id,
                        company_id,
                        currency_id,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN weighted_revenue ELSE 0 END),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN expected_revenue ELSE 0 END),
                        SUM(CASE WHEN state = 'won' THEN expected_revenue ELSE 0 END),
                        SUM(CASE WHEN state = 'lost' THEN expected_revenue ELSE 0 END),
                        SUM(revenue_at_risk),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') AND follow_up_overdue THEN 1 ELSE 0 END),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END)
                    FROM renewal_base
                    GROUP BY month_start, team_id, company_id, currency_id
                ),
                forecast_sales AS (
                    SELECT
                        month_start,
                        'sales_user'::varchar AS scope_type,
                        NULL::integer AS team_id,
                        sales_user_id,
                        company_id,
                        currency_id,
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN weighted_revenue ELSE 0 END),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN expected_revenue ELSE 0 END),
                        SUM(CASE WHEN state = 'won' THEN expected_revenue ELSE 0 END),
                        SUM(CASE WHEN state = 'lost' THEN expected_revenue ELSE 0 END),
                        SUM(revenue_at_risk),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') AND follow_up_overdue THEN 1 ELSE 0 END),
                        SUM(CASE WHEN state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END)
                    FROM renewal_base
                    GROUP BY month_start, sales_user_id, company_id, currency_id
                ),
                forecast_rows AS (
                    SELECT * FROM forecast_overall
                    UNION ALL
                    SELECT * FROM forecast_team
                    UNION ALL
                    SELECT * FROM forecast_sales
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    target.scope_type,
                    target.scope_sequence,
                    target.name,
                    target.month_start,
                    TO_CHAR(target.month_start, 'Mon YYYY') AS month_label,
                    target.team_id,
                    target.sales_user_id,
                    target.company_id,
                    target.currency_id,
                    target.target_amount,
                    target.budget_amount,
                    COALESCE(forecast.weighted_forecast_amount, 0.0) AS weighted_forecast_amount,
                    COALESCE(forecast.pipeline_amount, 0.0) AS pipeline_amount,
                    COALESCE(forecast.won_amount, 0.0) AS won_amount,
                    COALESCE(forecast.lost_amount, 0.0) AS lost_amount,
                    COALESCE(forecast.revenue_at_risk, 0.0) AS revenue_at_risk,
                    COALESCE(forecast.overdue_follow_up_count, 0) AS overdue_follow_up_count,
                    COALESCE(forecast.open_watch_count, 0) AS open_watch_count,
                    COALESCE(forecast.weighted_forecast_amount, 0.0) - target.target_amount AS gap_to_target,
                    COALESCE(forecast.weighted_forecast_amount, 0.0) - target.budget_amount AS gap_to_budget,
                    CASE WHEN target.target_amount > 0
                        THEN ROUND((COALESCE(forecast.weighted_forecast_amount, 0.0) / target.target_amount) * 100.0, 2)
                        ELSE 0.0
                    END AS attainment_rate,
                    CASE WHEN target.budget_amount > 0
                        THEN ROUND((COALESCE(forecast.weighted_forecast_amount, 0.0) / target.budget_amount) * 100.0, 2)
                        ELSE 0.0
                    END AS budget_attainment_rate
                FROM target_rows target
                LEFT JOIN forecast_rows forecast
                    ON forecast.month_start = target.month_start
                    AND forecast.scope_type = target.scope_type
                    AND COALESCE(forecast.team_id, 0) = COALESCE(target.team_id, 0)
                    AND COALESCE(forecast.sales_user_id, 0) = COALESCE(target.sales_user_id, 0)
                    AND forecast.company_id = target.company_id
            )
            """
        )

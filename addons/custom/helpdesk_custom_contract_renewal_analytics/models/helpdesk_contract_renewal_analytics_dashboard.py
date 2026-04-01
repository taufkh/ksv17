from odoo import _, api, fields, models, tools


class HelpdeskContractRenewalAnalyticsDashboard(models.Model):
    _name = "helpdesk.contract.renewal.analytics.dashboard"
    _description = "Helpdesk Contract Renewal Analytics Dashboard"
    _auto = False
    _order = "scope_sequence, name"

    scope_type = fields.Selection(
        [
            ("overall", "Overall"),
            ("team", "Team"),
            ("sales_user", "Salesperson"),
        ],
        readonly=True,
    )
    scope_sequence = fields.Integer(readonly=True)
    name = fields.Char(readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", readonly=True)
    sales_user_id = fields.Many2one("res.users", readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    currency_id = fields.Many2one("res.currency", readonly=True)
    open_count = fields.Integer(readonly=True)
    in_review_count = fields.Integer(readonly=True)
    handoff_count = fields.Integer(readonly=True)
    won_count = fields.Integer(readonly=True)
    lost_count = fields.Integer(readonly=True)
    critical_count = fields.Integer(readonly=True)
    overdue_follow_up_count = fields.Integer(readonly=True)
    expiring_7d_count = fields.Integer(readonly=True)
    expiring_14d_count = fields.Integer(readonly=True)
    total_expected_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    active_pipeline_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    weighted_pipeline_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    revenue_at_risk = fields.Monetary(currency_field="currency_id", readonly=True)
    won_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    lost_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    avg_probability = fields.Float(readonly=True)
    max_overdue_days = fields.Integer(readonly=True)

    @api.model
    def _ensure_renewal_analytics_enabled(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.renewal.analytics",
            message=_("Renewal analytics is disabled in Helpdesk feature settings."),
        )
        return True

    @api.model
    def action_open_renewal_overview_menu(self):
        self._ensure_renewal_analytics_enabled()
        return self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_contract_renewal_analytics.action_helpdesk_contract_renewal_overview"
        )

    @api.model
    def action_open_renewal_analytics_menu(self):
        self._ensure_renewal_analytics_enabled()
        return self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_contract_renewal_analytics.action_helpdesk_contract_renewal_analytics"
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH base AS (
                    SELECT
                        renewal.id,
                        renewal.company_id,
                        company.currency_id,
                        renewal.team_id,
                        renewal.sales_user_id,
                        renewal.state,
                        renewal.risk_level,
                        renewal.days_to_expiry,
                        renewal.follow_up_overdue,
                        renewal.follow_up_overdue_days,
                        renewal.renewal_probability,
                        COALESCE(renewal.expected_revenue, 0.0) AS expected_revenue,
                        COALESCE(renewal.weighted_revenue, 0.0) AS weighted_revenue,
                        COALESCE(renewal.revenue_at_risk, 0.0) AS revenue_at_risk
                    FROM helpdesk_contract_renewal renewal
                    LEFT JOIN res_company company ON company.id = renewal.company_id
                )
                SELECT
                    ROW_NUMBER() OVER () AS id,
                    dashboard.scope_type,
                    dashboard.scope_sequence,
                    dashboard.name,
                    dashboard.team_id,
                    dashboard.sales_user_id,
                    dashboard.company_id,
                    dashboard.currency_id,
                    dashboard.open_count,
                    dashboard.in_review_count,
                    dashboard.handoff_count,
                    dashboard.won_count,
                    dashboard.lost_count,
                    dashboard.critical_count,
                    dashboard.overdue_follow_up_count,
                    dashboard.expiring_7d_count,
                    dashboard.expiring_14d_count,
                    dashboard.total_expected_revenue,
                    dashboard.active_pipeline_revenue,
                    dashboard.weighted_pipeline_revenue,
                    dashboard.revenue_at_risk,
                    dashboard.won_revenue,
                    dashboard.lost_revenue,
                    dashboard.avg_probability,
                    dashboard.max_overdue_days
                FROM (
                    SELECT
                        'overall' AS scope_type,
                        1 AS scope_sequence,
                        'My Company Renewal Overview' AS name,
                        NULL::integer AS team_id,
                        NULL::integer AS sales_user_id,
                        base.company_id,
                        base.currency_id,
                        SUM(CASE WHEN base.state = 'open' THEN 1 ELSE 0 END) AS open_count,
                        SUM(CASE WHEN base.state = 'in_review' THEN 1 ELSE 0 END) AS in_review_count,
                        SUM(CASE WHEN base.state = 'handoff_sent' THEN 1 ELSE 0 END) AS handoff_count,
                        SUM(CASE WHEN base.state = 'won' THEN 1 ELSE 0 END) AS won_count,
                        SUM(CASE WHEN base.state = 'lost' THEN 1 ELSE 0 END) AS lost_count,
                        SUM(CASE WHEN base.risk_level = 'critical' AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END) AS critical_count,
                        SUM(CASE WHEN base.follow_up_overdue AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END) AS overdue_follow_up_count,
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 7 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END) AS expiring_7d_count,
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 14 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END) AS expiring_14d_count,
                        SUM(base.expected_revenue) AS total_expected_revenue,
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.expected_revenue ELSE 0 END) AS active_pipeline_revenue,
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.weighted_revenue ELSE 0 END) AS weighted_pipeline_revenue,
                        SUM(base.revenue_at_risk) AS revenue_at_risk,
                        SUM(CASE WHEN base.state = 'won' THEN base.expected_revenue ELSE 0 END) AS won_revenue,
                        SUM(CASE WHEN base.state = 'lost' THEN base.expected_revenue ELSE 0 END) AS lost_revenue,
                        AVG(base.renewal_probability)::float AS avg_probability,
                        MAX(base.follow_up_overdue_days) AS max_overdue_days
                    FROM base
                    GROUP BY base.company_id, base.currency_id

                    UNION ALL

                    SELECT
                        'team' AS scope_type,
                        2 AS scope_sequence,
                        COALESCE(team.name, 'No Team') AS name,
                        base.team_id,
                        NULL::integer AS sales_user_id,
                        base.company_id,
                        base.currency_id,
                        SUM(CASE WHEN base.state = 'open' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'in_review' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'handoff_sent' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'won' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'lost' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.risk_level = 'critical' AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.follow_up_overdue AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 7 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 14 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(base.expected_revenue),
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.expected_revenue ELSE 0 END),
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.weighted_revenue ELSE 0 END),
                        SUM(base.revenue_at_risk),
                        SUM(CASE WHEN base.state = 'won' THEN base.expected_revenue ELSE 0 END),
                        SUM(CASE WHEN base.state = 'lost' THEN base.expected_revenue ELSE 0 END),
                        AVG(base.renewal_probability)::float,
                        MAX(base.follow_up_overdue_days)
                    FROM base
                    LEFT JOIN helpdesk_ticket_team team ON team.id = base.team_id
                    GROUP BY base.company_id, base.currency_id, base.team_id, team.name

                    UNION ALL

                    SELECT
                        'sales_user' AS scope_type,
                        3 AS scope_sequence,
                        COALESCE(user_partner.name, 'Unassigned Salesperson') AS name,
                        NULL::integer AS team_id,
                        base.sales_user_id,
                        base.company_id,
                        base.currency_id,
                        SUM(CASE WHEN base.state = 'open' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'in_review' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'handoff_sent' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'won' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.state = 'lost' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.risk_level = 'critical' AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.follow_up_overdue AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 7 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(CASE WHEN base.days_to_expiry BETWEEN 0 AND 14 AND base.state IN ('open', 'in_review', 'handoff_sent') THEN 1 ELSE 0 END),
                        SUM(base.expected_revenue),
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.expected_revenue ELSE 0 END),
                        SUM(CASE WHEN base.state IN ('open', 'in_review', 'handoff_sent') THEN base.weighted_revenue ELSE 0 END),
                        SUM(base.revenue_at_risk),
                        SUM(CASE WHEN base.state = 'won' THEN base.expected_revenue ELSE 0 END),
                        SUM(CASE WHEN base.state = 'lost' THEN base.expected_revenue ELSE 0 END),
                        AVG(base.renewal_probability)::float,
                        MAX(base.follow_up_overdue_days)
                    FROM base
                    LEFT JOIN res_users sales_user ON sales_user.id = base.sales_user_id
                    LEFT JOIN res_partner user_partner ON user_partner.id = sales_user.partner_id
                    GROUP BY base.company_id, base.currency_id, base.sales_user_id, user_partner.name
                ) dashboard
            )
            """
        )

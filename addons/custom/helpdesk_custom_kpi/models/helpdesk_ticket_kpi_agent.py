from odoo import _, fields, models, tools


class HelpdeskTicketKpiAgent(models.Model):
    _name = "helpdesk.ticket.kpi.agent"
    _description = "Helpdesk Ticket KPI by Agent"
    _auto = False
    _rec_name = "scope_name"
    _order = "open_count desc, overdue_count desc, scope_name"

    scope_name = fields.Char(string="Agent", readonly=True)
    user_id = fields.Many2one("res.users", string="Assigned User", readonly=True)
    team_count = fields.Integer(string="Teams", readonly=True)
    total_count = fields.Integer(string="Total Tickets", readonly=True)
    open_count = fields.Integer(string="Open", readonly=True)
    overdue_count = fields.Integer(string="SLA Overdue", readonly=True)
    escalated_count = fields.Integer(string="Escalated", readonly=True)
    high_priority_open_count = fields.Integer(
        string="High Priority Open", readonly=True
    )
    customer_count = fields.Integer(string="Customers", readonly=True)
    closed_month_count = fields.Integer(string="Closed This Month", readonly=True)
    avg_assign_hours = fields.Float(string="Avg Assign Hours", readonly=True)
    avg_close_hours = fields.Float(string="Avg Close Hours", readonly=True)
    avg_rating = fields.Float(string="Avg Rating", readonly=True)
    breach_rate = fields.Float(string="Breach Rate", readonly=True)
    same_day_resolution_rate = fields.Float(
        string="Same Day Resolution Rate", readonly=True
    )

    def _ensure_kpi_feature_enabled(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.analytics.kpi",
            message=_("Helpdesk KPI reporting is disabled in Helpdesk feature settings."),
        )
        return True

    def _domain(self):
        self.ensure_one()
        if self.user_id:
            return [("user_id", "=", self.user_id.id)]
        return [("user_id", "=", False)]

    def _ticket_action(self, extra_domain=None, name=None):
        self.ensure_one()
        self._ensure_kpi_feature_enabled()
        action = self.env.ref("helpdesk_mgmt.helpdesk_ticket_action").read()[0]
        action["domain"] = self._domain() + (extra_domain or [])
        if name:
            action["name"] = name
        return action

    def action_view_queue(self):
        return self._ticket_action(
            extra_domain=[("stage_id.closed", "=", False)],
            name=_("%s Queue") % self.scope_name,
        )

    def action_view_overdue(self):
        return self._ticket_action(
            extra_domain=[("stage_id.closed", "=", False), ("sla_expired", "=", True)],
            name=_("%s SLA Watchlist") % self.scope_name,
        )

    def action_view_analysis(self):
        self.ensure_one()
        self._ensure_kpi_feature_enabled()
        action = self.env.ref("helpdesk_custom_kpi.action_helpdesk_ticket_kpi_analysis")
        result = action.read()[0]
        result["domain"] = self._domain()
        result["name"] = _("%s KPI Analysis") % self.scope_name
        return result

    def _query(self):
        return """
            WITH latest_rating AS (
                SELECT DISTINCT ON (rr.res_id)
                    rr.res_id,
                    rr.rating,
                    rr.consumed
                FROM rating_rating rr
                WHERE rr.res_model = 'helpdesk.ticket'
                ORDER BY rr.res_id, rr.id DESC
            ),
            ticket_base AS (
                SELECT
                    t.id,
                    t.user_id,
                    t.team_id,
                    t.commercial_partner_id,
                    COALESCE(s.closed, FALSE) AS closed,
                    COALESCE(t.sla_expired, FALSE) AS sla_expired,
                    COALESCE(t.escalated, FALSE) AS escalated,
                    (t.priority IN ('2', '3')) AS high_priority,
                    CASE
                        WHEN t.assigned_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0
                    END AS hours_to_assign,
                    CASE
                        WHEN t.closed_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 3600.0
                    END AS hours_to_close,
                    CASE
                        WHEN t.closed_date IS NOT NULL
                            AND EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 86400.0 <= 1
                        THEN 1 ELSE 0
                    END AS same_day_resolution_hit,
                    CASE
                        WHEN t.sla_deadline IS NOT NULL
                            AND COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC') > t.sla_deadline
                        THEN 1 ELSE 0
                    END AS breach_flag,
                    CASE
                        WHEN t.closed_date IS NOT NULL
                            AND DATE_TRUNC('month', t.closed_date) = DATE_TRUNC('month', CURRENT_DATE)
                        THEN 1 ELSE 0
                    END AS closed_this_month,
                    CASE WHEN lr.consumed IS TRUE THEN lr.rating END AS rating_value
                FROM helpdesk_ticket t
                LEFT JOIN helpdesk_ticket_stage s ON s.id = t.stage_id
                LEFT JOIN latest_rating lr ON lr.res_id = t.id
                WHERE t.active = TRUE
            )
            SELECT
                COALESCE(u.id, -1) AS id,
                COALESCE(rp.name, u.login, 'Unassigned Queue') AS scope_name,
                u.id AS user_id,
                COUNT(DISTINCT tb.team_id) AS team_count,
                COUNT(tb.id) AS total_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE) AS open_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE AND tb.sla_expired = TRUE) AS overdue_count,
                COUNT(*) FILTER (WHERE tb.escalated = TRUE) AS escalated_count,
                COUNT(*) FILTER (
                    WHERE tb.closed = FALSE AND tb.high_priority = TRUE
                ) AS high_priority_open_count,
                COUNT(DISTINCT tb.commercial_partner_id) AS customer_count,
                COALESCE(SUM(tb.closed_this_month), 0) AS closed_month_count,
                AVG(tb.hours_to_assign) AS avg_assign_hours,
                AVG(tb.hours_to_close) AS avg_close_hours,
                AVG(tb.rating_value) AS avg_rating,
                COALESCE(AVG(tb.breach_flag::float) * 100, 0) AS breach_rate,
                COALESCE(AVG(tb.same_day_resolution_hit::float) * 100, 0) AS same_day_resolution_rate
            FROM ticket_base tb
            LEFT JOIN res_users u ON u.id = tb.user_id
            LEFT JOIN res_partner rp ON rp.id = u.partner_id
            GROUP BY u.id, u.login, rp.name
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )

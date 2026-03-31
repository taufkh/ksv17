from odoo import _, fields, models, tools


class HelpdeskTicketKpiDashboard(models.Model):
    _name = "helpdesk.ticket.kpi.dashboard"
    _description = "Helpdesk Ticket KPI Dashboard"
    _auto = False
    _rec_name = "scope_name"
    _order = "scope_sequence, overdue_count desc, open_count desc, scope_name"

    scope_type = fields.Selection(
        [("overall", "Overall"), ("team", "Team")], readonly=True
    )
    scope_sequence = fields.Integer(readonly=True)
    scope_name = fields.Char(string="Scope", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Team", readonly=True)
    total_count = fields.Integer(string="Total Tickets", readonly=True)
    open_count = fields.Integer(string="Open", readonly=True)
    closed_count = fields.Integer(string="Closed", readonly=True)
    closed_month_count = fields.Integer(string="Closed This Month", readonly=True)
    overdue_count = fields.Integer(string="SLA Overdue", readonly=True)
    escalated_count = fields.Integer(string="Escalated", readonly=True)
    unassigned_count = fields.Integer(string="Unassigned", readonly=True)
    due_today_count = fields.Integer(string="Due Today", readonly=True)
    high_priority_open_count = fields.Integer(
        string="High Priority Open", readonly=True
    )
    backlog_7d_count = fields.Integer(string="Backlog > 7 Days", readonly=True)
    backlog_30d_count = fields.Integer(string="Backlog > 30 Days", readonly=True)
    customer_count = fields.Integer(string="Customers", readonly=True)
    rated_ticket_count = fields.Integer(string="Rated Tickets", readonly=True)
    avg_assign_hours = fields.Float(string="Avg Assign Hours", readonly=True)
    avg_close_hours = fields.Float(string="Avg Close Hours", readonly=True)
    avg_open_hours = fields.Float(string="Avg Open Hours", readonly=True)
    avg_rating = fields.Float(string="Avg Rating", readonly=True)
    breach_rate = fields.Float(string="Breach Rate", readonly=True)
    same_day_resolution_rate = fields.Float(
        string="Same Day Resolution Rate", readonly=True
    )
    assigned_within_4h_rate = fields.Float(
        string="Assigned Within 4h Rate", readonly=True
    )
    low_csat_open_count = fields.Integer(
        string="Low CSAT Open", readonly=True
    )
    recovery_sla_miss_count = fields.Integer(
        string="Recovery SLA Miss", readonly=True
    )
    no_followup_24h_count = fields.Integer(
        string="No Follow-up > 24h", readonly=True
    )

    def _ticket_domain(self):
        self.ensure_one()
        domain = []
        if self.scope_type == "team" and self.team_id:
            domain.append(("team_id", "=", self.team_id.id))
        return domain

    def _ticket_action(self, extra_domain=None, name=None):
        self.ensure_one()
        action = self.env.ref("helpdesk_mgmt.helpdesk_ticket_action").read()[0]
        action["domain"] = self._ticket_domain() + (extra_domain or [])
        if name:
            action["name"] = name
        return action

    def action_view_all_tickets(self):
        return self._ticket_action(name=_("%s Tickets") % self.scope_name)

    def action_view_open_tickets(self):
        return self._ticket_action(
            extra_domain=[("stage_id.closed", "=", False)],
            name=_("%s Open Tickets") % self.scope_name,
        )

    def action_view_overdue_tickets(self):
        return self._ticket_action(
            extra_domain=[("stage_id.closed", "=", False), ("sla_expired", "=", True)],
            name=_("%s SLA Watchlist") % self.scope_name,
        )

    def action_view_escalated_tickets(self):
        return self._ticket_action(
            extra_domain=[("escalated", "=", True)],
            name=_("%s Escalated Tickets") % self.scope_name,
        )

    def action_view_unassigned_tickets(self):
        return self._ticket_action(
            extra_domain=[("stage_id.closed", "=", False), ("user_id", "=", False)],
            name=_("%s Unassigned Tickets") % self.scope_name,
        )

    def action_view_high_priority_tickets(self):
        return self._ticket_action(
            extra_domain=[
                ("stage_id.closed", "=", False),
                ("priority", "in", ["2", "3"]),
            ],
            name=_("%s Priority Queue") % self.scope_name,
        )

    def action_open_analysis(self):
        self.ensure_one()
        action = self.env.ref("helpdesk_custom_kpi.action_helpdesk_ticket_kpi_analysis")
        result = action.read()[0]
        domain = []
        if self.scope_type == "team" and self.team_id:
            domain.append(("team_id", "=", self.team_id.id))
        result["domain"] = domain
        result["name"] = _("%s KPI Analysis") % self.scope_name
        return result

    def action_view_low_csat_open_tickets(self):
        return self._ticket_action(
            extra_domain=[
                ("activity_ids.summary", "=", "Low CSAT recovery required"),
                ("activity_ids.date_done", "=", False),
                ("activity_ids.active", "=", True),
            ],
            name=_("%s Low CSAT Open") % self.scope_name,
        )

    def action_view_recovery_sla_miss_tickets(self):
        return self._ticket_action(
            extra_domain=[
                ("activity_ids.summary", "=", "Low CSAT recovery required"),
                ("activity_ids.date_done", "=", False),
                ("activity_ids.active", "=", True),
                ("activity_ids.date_deadline", "<", fields.Date.today()),
            ],
            name=_("%s Recovery SLA Miss") % self.scope_name,
        )

    def action_view_no_followup_tickets(self):
        return self._ticket_action(
            extra_domain=[
                ("activity_ids.summary", "=", "Customer follow-up needed"),
                ("activity_ids.date_done", "=", False),
                ("activity_ids.active", "=", True),
            ],
            name=_("%s No Follow-up > 24h") % self.scope_name,
        )

    def _query(self):
        current_month = fields.Date.today().strftime("%Y-%m-01")
        return f"""
            WITH latest_rating AS (
                SELECT DISTINCT ON (rr.res_id)
                    rr.res_id,
                    rr.rating,
                    rr.consumed
                FROM rating_rating rr
                WHERE rr.res_model = 'helpdesk.ticket'
                ORDER BY rr.res_id, rr.id DESC
            ),
            activity_flag AS (
                SELECT
                    ma.res_id AS ticket_id,
                    MAX(
                        CASE
                            WHEN ma.summary = 'Low CSAT recovery required'
                                AND ma.active = TRUE
                                AND ma.date_done IS NULL
                            THEN 1 ELSE 0
                        END
                    ) AS low_csat_open_flag,
                    MAX(
                        CASE
                            WHEN ma.summary = 'Low CSAT recovery required'
                                AND ma.active = TRUE
                                AND ma.date_done IS NULL
                                AND ma.date_deadline < CURRENT_DATE
                            THEN 1 ELSE 0
                        END
                    ) AS recovery_sla_miss_flag,
                    MAX(
                        CASE
                            WHEN ma.summary = 'Customer follow-up needed'
                                AND ma.active = TRUE
                                AND ma.date_done IS NULL
                            THEN 1 ELSE 0
                        END
                    ) AS no_followup_24h_flag
                FROM mail_activity ma
                WHERE ma.res_model = 'helpdesk.ticket' AND ma.active = TRUE
                GROUP BY ma.res_id
            ),
            ticket_base AS (
                SELECT
                    t.id,
                    t.company_id,
                    t.team_id,
                    t.commercial_partner_id,
                    COALESCE(s.closed, FALSE) AS closed,
                    COALESCE(t.sla_expired, FALSE) AS sla_expired,
                    COALESCE(t.escalated, FALSE) AS escalated,
                    (t.priority IN ('2', '3')) AS high_priority,
                    (t.user_id IS NULL) AS unassigned,
                    CASE
                        WHEN t.assigned_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0
                    END AS hours_to_assign,
                    CASE
                        WHEN t.closed_date IS NOT NULL THEN
                            EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 3600.0
                    END AS hours_to_close,
                    EXTRACT(
                        EPOCH FROM (
                            COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                            - t.create_date
                        )
                    ) / 3600.0 AS hours_open,
                    CASE
                        WHEN t.sla_deadline IS NOT NULL
                            AND COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC') > t.sla_deadline
                        THEN 1 ELSE 0
                    END AS breach_flag,
                    CASE
                        WHEN t.closed_date IS NOT NULL
                            AND EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 86400.0 <= 1
                        THEN 1 ELSE 0
                    END AS same_day_resolution_hit,
                    CASE
                        WHEN t.assigned_date IS NOT NULL
                            AND EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0 <= 4
                        THEN 1 ELSE 0
                    END AS assigned_within_4h_hit,
                    CASE
                        WHEN COALESCE(s.closed, FALSE) = FALSE
                            AND EXTRACT(
                                EPOCH FROM ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - t.create_date)
                            ) / 86400.0 > 7
                        THEN 1 ELSE 0
                    END AS backlog_7d,
                    CASE
                        WHEN COALESCE(s.closed, FALSE) = FALSE
                            AND EXTRACT(
                                EPOCH FROM ((CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - t.create_date)
                            ) / 86400.0 > 30
                        THEN 1 ELSE 0
                    END AS backlog_30d,
                    CASE
                        WHEN COALESCE(s.closed, FALSE) = FALSE
                            AND t.sla_deadline IS NOT NULL
                            AND DATE(t.sla_deadline) = CURRENT_DATE
                        THEN 1 ELSE 0
                    END AS due_today,
                    CASE
                        WHEN t.closed_date IS NOT NULL
                            AND DATE_TRUNC('month', t.closed_date) = DATE '{current_month}'
                        THEN 1 ELSE 0
                    END AS closed_this_month,
                    CASE WHEN lr.consumed IS TRUE THEN 1 ELSE 0 END AS rated_ticket,
                    CASE WHEN lr.consumed IS TRUE THEN lr.rating END AS rating_value,
                    COALESCE(af.low_csat_open_flag, 0) AS low_csat_open_flag,
                    COALESCE(af.recovery_sla_miss_flag, 0) AS recovery_sla_miss_flag,
                    COALESCE(af.no_followup_24h_flag, 0) AS no_followup_24h_flag
                FROM helpdesk_ticket t
                LEFT JOIN helpdesk_ticket_stage s ON s.id = t.stage_id
                LEFT JOIN latest_rating lr ON lr.res_id = t.id
                LEFT JOIN activity_flag af ON af.ticket_id = t.id
                WHERE t.active = TRUE
            )
            SELECT
                -c.id AS id,
                'overall' AS scope_type,
                0 AS scope_sequence,
                CONCAT(c.name, ' Overview') AS scope_name,
                c.id AS company_id,
                NULL::integer AS team_id,
                COUNT(tb.id) AS total_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE) AS open_count,
                COUNT(*) FILTER (WHERE tb.closed = TRUE) AS closed_count,
                COALESCE(SUM(tb.closed_this_month), 0) AS closed_month_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE AND tb.sla_expired = TRUE) AS overdue_count,
                COUNT(*) FILTER (WHERE tb.escalated = TRUE) AS escalated_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE AND tb.unassigned = TRUE) AS unassigned_count,
                COALESCE(SUM(tb.due_today), 0) AS due_today_count,
                COUNT(*) FILTER (
                    WHERE tb.closed = FALSE AND tb.high_priority = TRUE
                ) AS high_priority_open_count,
                COALESCE(SUM(tb.backlog_7d), 0) AS backlog_7d_count,
                COALESCE(SUM(tb.backlog_30d), 0) AS backlog_30d_count,
                COUNT(DISTINCT tb.commercial_partner_id) AS customer_count,
                COALESCE(SUM(tb.rated_ticket), 0) AS rated_ticket_count,
                AVG(tb.hours_to_assign) AS avg_assign_hours,
                AVG(tb.hours_to_close) AS avg_close_hours,
                AVG(tb.hours_open) AS avg_open_hours,
                AVG(tb.rating_value) AS avg_rating,
                COALESCE(AVG(tb.breach_flag::float) * 100, 0) AS breach_rate,
                COALESCE(AVG(tb.same_day_resolution_hit::float) * 100, 0) AS same_day_resolution_rate,
                COALESCE(AVG(tb.assigned_within_4h_hit::float) * 100, 0) AS assigned_within_4h_rate,
                COALESCE(SUM(tb.low_csat_open_flag), 0) AS low_csat_open_count,
                COALESCE(SUM(tb.recovery_sla_miss_flag), 0) AS recovery_sla_miss_count,
                COALESCE(SUM(tb.no_followup_24h_flag), 0) AS no_followup_24h_count
            FROM res_company c
            LEFT JOIN ticket_base tb ON tb.company_id = c.id
            GROUP BY c.id, c.name

            UNION ALL

            SELECT
                team.id AS id,
                'team' AS scope_type,
                10 AS scope_sequence,
                team.name AS scope_name,
                team.company_id AS company_id,
                team.id AS team_id,
                COUNT(tb.id) AS total_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE) AS open_count,
                COUNT(*) FILTER (WHERE tb.closed = TRUE) AS closed_count,
                COALESCE(SUM(tb.closed_this_month), 0) AS closed_month_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE AND tb.sla_expired = TRUE) AS overdue_count,
                COUNT(*) FILTER (WHERE tb.escalated = TRUE) AS escalated_count,
                COUNT(*) FILTER (WHERE tb.closed = FALSE AND tb.unassigned = TRUE) AS unassigned_count,
                COALESCE(SUM(tb.due_today), 0) AS due_today_count,
                COUNT(*) FILTER (
                    WHERE tb.closed = FALSE AND tb.high_priority = TRUE
                ) AS high_priority_open_count,
                COALESCE(SUM(tb.backlog_7d), 0) AS backlog_7d_count,
                COALESCE(SUM(tb.backlog_30d), 0) AS backlog_30d_count,
                COUNT(DISTINCT tb.commercial_partner_id) AS customer_count,
                COALESCE(SUM(tb.rated_ticket), 0) AS rated_ticket_count,
                AVG(tb.hours_to_assign) AS avg_assign_hours,
                AVG(tb.hours_to_close) AS avg_close_hours,
                AVG(tb.hours_open) AS avg_open_hours,
                AVG(tb.rating_value) AS avg_rating,
                COALESCE(AVG(tb.breach_flag::float) * 100, 0) AS breach_rate,
                COALESCE(AVG(tb.same_day_resolution_hit::float) * 100, 0) AS same_day_resolution_rate,
                COALESCE(AVG(tb.assigned_within_4h_hit::float) * 100, 0) AS assigned_within_4h_rate,
                COALESCE(SUM(tb.low_csat_open_flag), 0) AS low_csat_open_count,
                COALESCE(SUM(tb.recovery_sla_miss_flag), 0) AS recovery_sla_miss_count,
                COALESCE(SUM(tb.no_followup_24h_flag), 0) AS no_followup_24h_count
            FROM helpdesk_ticket_team team
            LEFT JOIN ticket_base tb ON tb.team_id = team.id
            WHERE team.active = TRUE
            GROUP BY team.id, team.name, team.company_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )

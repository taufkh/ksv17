from odoo import fields, models, tools


class HelpdeskTicketKpiReport(models.Model):
    _name = "helpdesk.ticket.kpi.report"
    _description = "Helpdesk Ticket KPI Report"
    _auto = False
    _rec_name = "ticket_id"
    _order = "create_date desc, id desc"

    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket", readonly=True)
    number = fields.Char(string="Ticket Number", readonly=True)
    name = fields.Char(string="Title", readonly=True)
    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    commercial_partner_id = fields.Many2one(
        "res.partner", string="Commercial Entity", readonly=True
    )
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Team", readonly=True)
    user_id = fields.Many2one("res.users", string="Assigned User", readonly=True)
    category_id = fields.Many2one(
        "helpdesk.ticket.category", string="Category", readonly=True
    )
    type_id = fields.Many2one("helpdesk.ticket.type", string="Type", readonly=True)
    channel_id = fields.Many2one(
        "helpdesk.ticket.channel", string="Channel", readonly=True
    )
    stage_id = fields.Many2one("helpdesk.ticket.stage", string="Stage", readonly=True)
    priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Medium"),
            ("2", "High"),
            ("3", "Very High"),
        ],
        string="Priority",
        readonly=True,
    )
    age_bucket = fields.Selection(
        selection=[
            ("fresh", "0-1 Day"),
            ("warming", "2-3 Days"),
            ("aging", "4-7 Days"),
            ("stale", ">7 Days"),
        ],
        string="Aging Bucket",
        readonly=True,
    )
    assignment_bucket = fields.Selection(
        selection=[
            ("instant", "< 1 Hour"),
            ("fast", "1-4 Hours"),
            ("slow", "4-24 Hours"),
            ("lagging", "> 24 Hours"),
            ("unassigned", "Unassigned"),
        ],
        string="Assignment Speed",
        readonly=True,
    )
    resolution_bucket = fields.Selection(
        selection=[
            ("same_day", "Same Day"),
            ("one_to_three", "1-3 Days"),
            ("four_to_seven", "4-7 Days"),
            ("over_week", "> 7 Days"),
            ("still_open", "Still Open"),
        ],
        string="Resolution Bucket",
        readonly=True,
    )
    sla_status = fields.Selection(
        selection=[
            ("within", "Within SLA"),
            ("breached", "Breached SLA"),
            ("no_sla", "No SLA"),
        ],
        string="SLA Status",
        readonly=True,
    )
    rating_bucket = fields.Selection(
        selection=[
            ("excellent", "Excellent"),
            ("neutral", "Neutral"),
            ("bad", "Bad"),
            ("unrated", "Unrated"),
        ],
        string="Rating Band",
        readonly=True,
    )
    create_date = fields.Datetime(string="Submitted On", readonly=True)
    assigned_date = fields.Datetime(string="Assigned On", readonly=True)
    closed_date = fields.Datetime(string="Closed On", readonly=True)
    submit_date = fields.Date(string="Submitted Date", readonly=True)
    deadline_date = fields.Date(string="Deadline Date", readonly=True)
    sla_deadline = fields.Datetime(string="SLA Deadline", readonly=True)
    last_escalation_at = fields.Datetime(string="Last Escalation", readonly=True)
    closed = fields.Boolean(string="Closed", readonly=True)
    unattended = fields.Boolean(string="Unattended", readonly=True)
    sla_expired = fields.Boolean(string="SLA Overdue", readonly=True)
    escalated = fields.Boolean(string="Escalated", readonly=True)
    high_priority = fields.Boolean(string="High Priority", readonly=True)
    is_rated = fields.Boolean(string="Rated", readonly=True)

    ticket_count = fields.Integer(string="Tickets", readonly=True)
    breach_flag = fields.Integer(string="Breaches", readonly=True)
    overdue_open_flag = fields.Integer(string="Open Breaches", readonly=True)
    same_day_resolution_hit = fields.Integer(
        string="Same Day Resolution", readonly=True
    )
    assigned_within_4h_hit = fields.Integer(
        string="Assigned Within 4h", readonly=True
    )
    rated_ticket_count = fields.Integer(string="Rated Tickets", readonly=True)
    age_days = fields.Float(string="Age (Days)", readonly=True, group_operator="avg")
    hours_to_assign = fields.Float(
        string="Hours to Assign", readonly=True, group_operator="avg"
    )
    hours_to_close = fields.Float(
        string="Hours to Close", readonly=True, group_operator="avg"
    )
    hours_open = fields.Float(
        string="Hours Open", readonly=True, group_operator="avg"
    )
    sla_target_hours = fields.Float(
        string="SLA Target (Hours)", readonly=True, group_operator="avg"
    )
    sla_delay_hours = fields.Float(
        string="SLA Delay (Hours)", readonly=True, group_operator="avg"
    )
    rating_value = fields.Float(string="Customer Rating", readonly=True)

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
            )
            SELECT
                t.id AS id,
                t.id AS ticket_id,
                t.number AS number,
                t.name AS name,
                t.partner_id AS partner_id,
                t.commercial_partner_id AS commercial_partner_id,
                t.company_id AS company_id,
                t.team_id AS team_id,
                t.user_id AS user_id,
                t.category_id AS category_id,
                t.type_id AS type_id,
                t.channel_id AS channel_id,
                t.stage_id AS stage_id,
                t.priority AS priority,
                CASE
                    WHEN EXTRACT(
                        EPOCH FROM (
                            COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                            - t.create_date
                        )
                    ) / 86400.0 <= 1 THEN 'fresh'
                    WHEN EXTRACT(
                        EPOCH FROM (
                            COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                            - t.create_date
                        )
                    ) / 86400.0 <= 3 THEN 'warming'
                    WHEN EXTRACT(
                        EPOCH FROM (
                            COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                            - t.create_date
                        )
                    ) / 86400.0 <= 7 THEN 'aging'
                    ELSE 'stale'
                END AS age_bucket,
                CASE
                    WHEN t.assigned_date IS NULL THEN 'unassigned'
                    WHEN EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0 < 1 THEN 'instant'
                    WHEN EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0 <= 4 THEN 'fast'
                    WHEN EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0 <= 24 THEN 'slow'
                    ELSE 'lagging'
                END AS assignment_bucket,
                CASE
                    WHEN t.closed_date IS NULL THEN 'still_open'
                    WHEN EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 86400.0 <= 1 THEN 'same_day'
                    WHEN EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 86400.0 <= 3 THEN 'one_to_three'
                    WHEN EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 86400.0 <= 7 THEN 'four_to_seven'
                    ELSE 'over_week'
                END AS resolution_bucket,
                CASE
                    WHEN t.sla_deadline IS NULL THEN 'no_sla'
                    WHEN COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC') <= t.sla_deadline THEN 'within'
                    ELSE 'breached'
                END AS sla_status,
                CASE
                    WHEN lr.consumed IS NOT TRUE THEN 'unrated'
                    WHEN lr.rating >= 4 THEN 'excellent'
                    WHEN lr.rating >= 2.5 THEN 'neutral'
                    ELSE 'bad'
                END AS rating_bucket,
                t.create_date AS create_date,
                t.assigned_date AS assigned_date,
                t.closed_date AS closed_date,
                DATE(t.create_date) AS submit_date,
                DATE(t.sla_deadline) AS deadline_date,
                t.sla_deadline AS sla_deadline,
                t.last_escalation_at AS last_escalation_at,
                COALESCE(s.closed, FALSE) AS closed,
                COALESCE(t.unattended, FALSE) AS unattended,
                COALESCE(t.sla_expired, FALSE) AS sla_expired,
                COALESCE(t.escalated, FALSE) AS escalated,
                (t.priority IN ('2', '3')) AS high_priority,
                COALESCE(lr.consumed, FALSE) AS is_rated,
                1 AS ticket_count,
                CASE
                    WHEN t.sla_deadline IS NOT NULL
                        AND COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC') > t.sla_deadline
                    THEN 1 ELSE 0
                END AS breach_flag,
                CASE
                    WHEN COALESCE(s.closed, FALSE) = FALSE
                        AND t.sla_deadline IS NOT NULL
                        AND CURRENT_TIMESTAMP AT TIME ZONE 'UTC' > t.sla_deadline
                    THEN 1 ELSE 0
                END AS overdue_open_flag,
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
                CASE WHEN lr.consumed IS TRUE THEN 1 ELSE 0 END AS rated_ticket_count,
                EXTRACT(
                    EPOCH FROM (
                        COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                        - t.create_date
                    )
                ) / 86400.0 AS age_days,
                EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0
                    AS hours_to_assign,
                EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 3600.0
                    AS hours_to_close,
                EXTRACT(
                    EPOCH FROM (
                        COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                        - t.create_date
                    )
                ) / 3600.0 AS hours_open,
                CASE
                    WHEN t.sla_deadline IS NOT NULL THEN
                        EXTRACT(EPOCH FROM (t.sla_deadline - t.create_date)) / 3600.0
                END AS sla_target_hours,
                CASE
                    WHEN t.sla_deadline IS NOT NULL THEN
                        GREATEST(
                            EXTRACT(
                                EPOCH FROM (
                                    COALESCE(
                                        t.closed_date,
                                        CURRENT_TIMESTAMP AT TIME ZONE 'UTC'
                                    ) - t.sla_deadline
                                )
                            ) / 3600.0,
                            0
                        )
                    ELSE 0
                END AS sla_delay_hours,
                CASE WHEN lr.consumed IS TRUE THEN lr.rating ELSE NULL END AS rating_value
            FROM helpdesk_ticket t
            LEFT JOIN helpdesk_ticket_stage s ON s.id = t.stage_id
            LEFT JOIN latest_rating lr ON lr.res_id = t.id
            WHERE t.active = TRUE
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )

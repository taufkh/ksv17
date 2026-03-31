from odoo import fields, models, tools


class HelpdeskTicketKpiTrend(models.Model):
    _name = "helpdesk.ticket.kpi.trend"
    _description = "Helpdesk Ticket KPI Trend"
    _auto = False
    _rec_name = "period_date"
    _order = "period_date desc, team_id"

    period_date = fields.Date(string="Date", readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Team", readonly=True)
    submitted_count = fields.Integer(string="Submitted", readonly=True)
    closed_count = fields.Integer(string="Closed", readonly=True)
    escalated_count = fields.Integer(string="Escalated", readonly=True)
    overdue_count = fields.Integer(string="Overdue", readonly=True)
    rated_count = fields.Integer(string="Rated", readonly=True)
    avg_assign_hours = fields.Float(string="Avg Assign Hours", readonly=True)
    avg_close_hours = fields.Float(string="Avg Close Hours", readonly=True)
    avg_rating = fields.Float(string="Avg Rating", readonly=True)

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
                ROW_NUMBER() OVER (ORDER BY DATE(t.create_date), t.team_id NULLS FIRST) AS id,
                DATE(t.create_date) AS period_date,
                t.team_id AS team_id,
                COUNT(t.id) AS submitted_count,
                COUNT(*) FILTER (WHERE t.closed_date IS NOT NULL) AS closed_count,
                COUNT(*) FILTER (WHERE COALESCE(t.escalated, FALSE) = TRUE) AS escalated_count,
                COUNT(*) FILTER (WHERE COALESCE(t.sla_expired, FALSE) = TRUE) AS overdue_count,
                COUNT(*) FILTER (WHERE lr.consumed IS TRUE) AS rated_count,
                AVG(EXTRACT(EPOCH FROM (t.assigned_date - t.create_date)) / 3600.0) AS avg_assign_hours,
                AVG(EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 3600.0) AS avg_close_hours,
                AVG(CASE WHEN lr.consumed IS TRUE THEN lr.rating END) AS avg_rating
            FROM helpdesk_ticket t
            LEFT JOIN latest_rating lr ON lr.res_id = t.id
            WHERE t.active = TRUE
            GROUP BY DATE(t.create_date), t.team_id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )

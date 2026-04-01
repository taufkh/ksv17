from odoo import _, fields, models, tools


class HelpdeskTicketKpiCustomer(models.Model):
    _name = "helpdesk.ticket.kpi.customer"
    _description = "Helpdesk Ticket KPI by Customer"
    _auto = False
    _rec_name = "partner_id"
    _order = "open_count desc, overdue_count desc, total_count desc"

    partner_id = fields.Many2one("res.partner", string="Customer", readonly=True)
    team_count = fields.Integer(string="Teams", readonly=True)
    total_count = fields.Integer(string="Total Tickets", readonly=True)
    open_count = fields.Integer(string="Open", readonly=True)
    overdue_count = fields.Integer(string="SLA Overdue", readonly=True)
    escalated_count = fields.Integer(string="Escalated", readonly=True)
    high_priority_count = fields.Integer(string="High Priority", readonly=True)
    channel_count = fields.Integer(string="Channels", readonly=True)
    avg_close_hours = fields.Float(string="Avg Close Hours", readonly=True)
    avg_rating = fields.Float(string="Avg Rating", readonly=True)
    breach_rate = fields.Float(string="Breach Rate", readonly=True)
    last_ticket_date = fields.Datetime(string="Last Ticket", readonly=True)

    def _ensure_kpi_feature_enabled(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.analytics.kpi",
            message=_("Helpdesk KPI reporting is disabled in Helpdesk feature settings."),
        )
        return True

    def _domain(self):
        self.ensure_one()
        return [("commercial_partner_id", "=", self.partner_id.id)]

    def action_view_tickets(self):
        self.ensure_one()
        self._ensure_kpi_feature_enabled()
        action = self.env.ref("helpdesk_mgmt.helpdesk_ticket_action").read()[0]
        action["domain"] = self._domain()
        action["name"] = _("%s Tickets") % self.partner_id.name
        return action

    def action_view_analysis(self):
        self.ensure_one()
        self._ensure_kpi_feature_enabled()
        action = self.env.ref("helpdesk_custom_kpi.action_helpdesk_ticket_kpi_analysis")
        result = action.read()[0]
        result["domain"] = self._domain()
        result["name"] = _("%s KPI Analysis") % self.partner_id.name
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
            )
            SELECT
                p.id AS id,
                p.id AS partner_id,
                COUNT(DISTINCT t.team_id) AS team_count,
                COUNT(t.id) AS total_count,
                COUNT(*) FILTER (WHERE COALESCE(s.closed, FALSE) = FALSE) AS open_count,
                COUNT(*) FILTER (
                    WHERE COALESCE(s.closed, FALSE) = FALSE AND COALESCE(t.sla_expired, FALSE) = TRUE
                ) AS overdue_count,
                COUNT(*) FILTER (WHERE COALESCE(t.escalated, FALSE) = TRUE) AS escalated_count,
                COUNT(*) FILTER (WHERE t.priority IN ('2', '3')) AS high_priority_count,
                COUNT(DISTINCT t.channel_id) AS channel_count,
                AVG(EXTRACT(EPOCH FROM (t.closed_date - t.create_date)) / 3600.0) AS avg_close_hours,
                AVG(CASE WHEN lr.consumed IS TRUE THEN lr.rating END) AS avg_rating,
                COALESCE(
                    AVG(
                        CASE
                            WHEN t.sla_deadline IS NOT NULL
                                AND COALESCE(t.closed_date, CURRENT_TIMESTAMP AT TIME ZONE 'UTC') > t.sla_deadline
                            THEN 1.0 ELSE 0.0
                        END
                    ) * 100,
                    0
                ) AS breach_rate,
                MAX(t.create_date) AS last_ticket_date
            FROM res_partner p
            JOIN helpdesk_ticket t
                ON t.commercial_partner_id = p.id AND t.active = TRUE
            LEFT JOIN helpdesk_ticket_stage s ON s.id = t.stage_id
            LEFT JOIN latest_rating lr ON lr.res_id = t.id
            GROUP BY p.id
        """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"CREATE OR REPLACE VIEW {self._table} AS ({self._query()})"
        )

from odoo import _, api, fields, models, tools


class HelpdeskCommunicationAnalyticsReport(models.Model):
    _name = "helpdesk.communication.analytics.report"
    _description = "Helpdesk Communication Analytics Report"
    _auto = False
    _order = "response_due desc, stale_after_24h desc, create_date desc"

    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket", readonly=True)
    number = fields.Char(readonly=True)
    name = fields.Char(readonly=True)
    create_date = fields.Datetime(readonly=True)
    team_id = fields.Many2one("helpdesk.ticket.team", readonly=True)
    partner_id = fields.Many2one("res.partner", readonly=True)
    user_id = fields.Many2one("res.users", string="Assigned User", readonly=True)
    stage_id = fields.Many2one("helpdesk.ticket.stage", readonly=True)
    priority = fields.Selection(
        selection=[("0", "Low"), ("1", "Normal"), ("2", "High"), ("3", "Very High")],
        readonly=True,
    )
    closed = fields.Boolean(readonly=True)
    last_communication_channel = fields.Selection(
        selection=[
            ("portal", "Portal"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("api", "API"),
            ("manual", "Manual"),
        ],
        readonly=True,
    )
    communication_count = fields.Integer(readonly=True)
    inbound_count = fields.Integer(readonly=True)
    outbound_count = fields.Integer(readonly=True)
    failed_count = fields.Integer(readonly=True)
    portal_count = fields.Integer(readonly=True)
    whatsapp_count = fields.Integer(readonly=True)
    email_count = fields.Integer(readonly=True)
    phone_count = fields.Integer(readonly=True)
    api_count = fields.Integer(readonly=True)
    manual_count = fields.Integer(readonly=True)
    first_inbound_at = fields.Datetime(readonly=True)
    first_outbound_at = fields.Datetime(readonly=True)
    last_customer_response_at = fields.Datetime(readonly=True)
    last_outbound_at = fields.Datetime(readonly=True)
    last_communication_at = fields.Datetime(readonly=True)
    first_response_hours = fields.Float(readonly=True, group_operator="avg")
    no_update_hours = fields.Float(readonly=True, group_operator="avg")
    customer_silence_hours = fields.Float(readonly=True, group_operator="avg")
    response_due = fields.Boolean(readonly=True)
    waiting_customer = fields.Boolean(readonly=True)
    stale_after_24h = fields.Boolean(readonly=True)
    no_communication = fields.Boolean(readonly=True)
    response_bucket = fields.Selection(
        selection=[
            ("no_outbound", "No Outbound Update"),
            ("within_1h", "Within 1 Hour"),
            ("within_4h", "Within 4 Hours"),
            ("within_24h", "Within 24 Hours"),
            ("after_24h", "After 24 Hours"),
        ],
        readonly=True,
    )
    inactivity_bucket = fields.Selection(
        selection=[
            ("none", "No Communication Yet"),
            ("lt_4h", "Under 4 Hours"),
            ("btw_4_24h", "4 to 24 Hours"),
            ("btw_1_3d", "1 to 3 Days"),
            ("gt_3d", "More Than 3 Days"),
        ],
        readonly=True,
    )

    @api.model
    def action_open_communication_analytics_menu(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.analytics.communication",
            message=_(
                "Communication analytics is disabled in Helpdesk feature settings."
            ),
        )
        return self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_communication_analytics.action_helpdesk_communication_analytics_report"
        )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
            CREATE OR REPLACE VIEW %(table)s AS (
                WITH log_summary AS (
                    SELECT
                        log.ticket_id,
                        COUNT(log.id) AS communication_count,
                        COUNT(*) FILTER (WHERE log.direction = 'inbound') AS inbound_count,
                        COUNT(*) FILTER (WHERE log.direction = 'outbound') AS outbound_count,
                        COUNT(*) FILTER (WHERE log.status IN ('failed', 'cancelled')) AS failed_count,
                        COUNT(*) FILTER (WHERE log.channel = 'portal') AS portal_count,
                        COUNT(*) FILTER (WHERE log.channel = 'whatsapp') AS whatsapp_count,
                        COUNT(*) FILTER (WHERE log.channel = 'email') AS email_count,
                        COUNT(*) FILTER (WHERE log.channel = 'phone') AS phone_count,
                        COUNT(*) FILTER (WHERE log.channel = 'api') AS api_count,
                        COUNT(*) FILTER (WHERE log.channel = 'manual') AS manual_count,
                        MIN(log.logged_at) FILTER (WHERE log.direction = 'inbound') AS first_inbound_at,
                        MIN(log.logged_at) FILTER (WHERE log.direction = 'outbound') AS first_outbound_at,
                        MAX(log.logged_at) FILTER (WHERE log.direction = 'inbound') AS last_customer_response_at,
                        MAX(log.logged_at) FILTER (WHERE log.direction = 'outbound') AS last_outbound_at,
                        MAX(log.logged_at) AS last_communication_at
                    FROM helpdesk_communication_log log
                    GROUP BY log.ticket_id
                )
                SELECT
                    t.id AS id,
                    t.id AS ticket_id,
                    t.number AS number,
                    t.name AS name,
                    t.create_date AS create_date,
                    t.team_id AS team_id,
                    t.partner_id AS partner_id,
                    t.user_id AS user_id,
                    t.stage_id AS stage_id,
                    t.priority AS priority,
                    COALESCE(stage.closed, FALSE) AS closed,
                    t.last_communication_channel AS last_communication_channel,
                    COALESCE(ls.communication_count, 0) AS communication_count,
                    COALESCE(ls.inbound_count, 0) AS inbound_count,
                    COALESCE(ls.outbound_count, 0) AS outbound_count,
                    COALESCE(ls.failed_count, 0) AS failed_count,
                    COALESCE(ls.portal_count, 0) AS portal_count,
                    COALESCE(ls.whatsapp_count, 0) AS whatsapp_count,
                    COALESCE(ls.email_count, 0) AS email_count,
                    COALESCE(ls.phone_count, 0) AS phone_count,
                    COALESCE(ls.api_count, 0) AS api_count,
                    COALESCE(ls.manual_count, 0) AS manual_count,
                    ls.first_inbound_at AS first_inbound_at,
                    ls.first_outbound_at AS first_outbound_at,
                    ls.last_customer_response_at AS last_customer_response_at,
                    ls.last_outbound_at AS last_outbound_at,
                    ls.last_communication_at AS last_communication_at,
                    CASE
                        WHEN ls.first_outbound_at IS NULL OR t.create_date IS NULL THEN NULL
                        ELSE EXTRACT(EPOCH FROM (ls.first_outbound_at - t.create_date)) / 3600.0
                    END AS first_response_hours,
                    CASE
                        WHEN COALESCE(stage.closed, FALSE) THEN 0.0
                        WHEN ls.last_communication_at IS NOT NULL THEN EXTRACT(EPOCH FROM (timezone('UTC', now()) - ls.last_communication_at)) / 3600.0
                        ELSE EXTRACT(EPOCH FROM (timezone('UTC', now()) - t.create_date)) / 3600.0
                    END AS no_update_hours,
                    CASE
                        WHEN COALESCE(stage.closed, FALSE) OR ls.last_outbound_at IS NULL THEN 0.0
                        WHEN ls.last_customer_response_at IS NULL OR ls.last_outbound_at >= ls.last_customer_response_at
                            THEN EXTRACT(EPOCH FROM (timezone('UTC', now()) - ls.last_outbound_at)) / 3600.0
                        ELSE 0.0
                    END AS customer_silence_hours,
                    CASE
                        WHEN COALESCE(stage.closed, FALSE) THEN FALSE
                        WHEN COALESCE(ls.communication_count, 0) = 0 THEN TRUE
                        WHEN ls.last_customer_response_at IS NOT NULL
                             AND (ls.last_outbound_at IS NULL OR ls.last_customer_response_at > ls.last_outbound_at) THEN TRUE
                        ELSE FALSE
                    END AS response_due,
                    CASE
                        WHEN COALESCE(stage.closed, FALSE) OR ls.last_outbound_at IS NULL THEN FALSE
                        WHEN ls.last_customer_response_at IS NULL OR ls.last_outbound_at >= ls.last_customer_response_at THEN TRUE
                        ELSE FALSE
                    END AS waiting_customer,
                    CASE
                        WHEN COALESCE(stage.closed, FALSE) THEN FALSE
                        WHEN ls.last_communication_at IS NOT NULL
                             AND (timezone('UTC', now()) - ls.last_communication_at) > INTERVAL '24 hours' THEN TRUE
                        WHEN ls.last_communication_at IS NULL
                             AND (timezone('UTC', now()) - t.create_date) > INTERVAL '24 hours' THEN TRUE
                        ELSE FALSE
                    END AS stale_after_24h,
                    CASE
                        WHEN COALESCE(ls.communication_count, 0) = 0 THEN TRUE
                        ELSE FALSE
                    END AS no_communication,
                    CASE
                        WHEN ls.first_outbound_at IS NULL OR t.create_date IS NULL THEN 'no_outbound'
                        WHEN (ls.first_outbound_at - t.create_date) <= INTERVAL '1 hour' THEN 'within_1h'
                        WHEN (ls.first_outbound_at - t.create_date) <= INTERVAL '4 hours' THEN 'within_4h'
                        WHEN (ls.first_outbound_at - t.create_date) <= INTERVAL '24 hours' THEN 'within_24h'
                        ELSE 'after_24h'
                    END AS response_bucket,
                    CASE
                        WHEN ls.last_communication_at IS NULL THEN 'none'
                        WHEN (timezone('UTC', now()) - ls.last_communication_at) <= INTERVAL '4 hours' THEN 'lt_4h'
                        WHEN (timezone('UTC', now()) - ls.last_communication_at) <= INTERVAL '24 hours' THEN 'btw_4_24h'
                        WHEN (timezone('UTC', now()) - ls.last_communication_at) <= INTERVAL '72 hours' THEN 'btw_1_3d'
                        ELSE 'gt_3d'
                    END AS inactivity_bucket
                FROM helpdesk_ticket t
                LEFT JOIN helpdesk_ticket_stage stage ON stage.id = t.stage_id
                LEFT JOIN log_summary ls ON ls.ticket_id = t.id
            )
            """
            % {"table": self._table}
        )

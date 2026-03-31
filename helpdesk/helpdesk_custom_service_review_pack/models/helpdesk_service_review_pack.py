from datetime import datetime, time, timedelta

from odoo import _, api, fields, models


class HelpdeskServiceReviewPack(models.Model):
    _name = "helpdesk.service.review.pack"
    _description = "Helpdesk Service Review Pack"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "prepared_at desc, id desc"

    health_selection = [
        ("quiet", "Quiet"),
        ("stable", "Stable"),
        ("attention", "Needs Attention"),
        ("critical", "Critical"),
    ]
    renewal_risk_selection = [
        ("stable", "Stable"),
        ("watch", "Watch"),
        ("at_risk", "At Risk"),
        ("critical", "Critical"),
    ]
    state = fields.Selection(
        [("draft", "Draft"), ("generated", "Generated")],
        default="draft",
        required=True,
        tracking=True,
    )
    name = fields.Char(required=True, copy=False, default=lambda self: _("New"))
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        domain=[("is_company", "=", True)],
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        compute="_compute_company_id",
        store=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )
    date_from = fields.Date(required=True, tracking=True, default=lambda self: fields.Date.start_of(fields.Date.context_today(self), "month"))
    date_to = fields.Date(required=True, tracking=True, default=fields.Date.context_today)
    prepared_at = fields.Datetime(readonly=True, tracking=True)
    prepared_by_id = fields.Many2one("res.users", string="Prepared By", readonly=True)
    health = fields.Selection(selection=health_selection, readonly=True)
    renewal_risk_segment = fields.Selection(selection=renewal_risk_selection, readonly=True)
    tickets_created_count = fields.Integer(readonly=True)
    tickets_closed_count = fields.Integer(readonly=True)
    current_open_ticket_count = fields.Integer(readonly=True)
    current_overdue_ticket_count = fields.Integer(readonly=True)
    current_escalated_ticket_count = fields.Integer(readonly=True)
    current_unassigned_ticket_count = fields.Integer(readonly=True)
    avg_resolution_hours = fields.Float(readonly=True, digits=(16, 2))
    avg_rating = fields.Float(readonly=True, digits=(16, 2))
    portal_views_total = fields.Integer(readonly=True)
    communication_count = fields.Integer(readonly=True)
    inbound_communication_count = fields.Integer(readonly=True)
    outbound_communication_count = fields.Integer(readonly=True)
    failed_communication_count = fields.Integer(readonly=True)
    dispatch_count = fields.Integer(readonly=True)
    completed_dispatch_count = fields.Integer(readonly=True)
    pending_approval_count = fields.Integer(readonly=True)
    active_contract_count = fields.Integer(readonly=True)
    contract_consumed_hours = fields.Float(readonly=True, digits=(16, 2))
    contract_remaining_hours = fields.Float(readonly=True, digits=(16, 2))
    uninvoiced_hours = fields.Float(readonly=True, digits=(16, 2))
    invoice_count = fields.Integer(readonly=True)
    invoiced_amount = fields.Monetary(currency_field="currency_id", readonly=True)
    renewal_watch_count = fields.Integer(readonly=True)
    renewal_overdue_followup_count = fields.Integer(readonly=True)
    renewal_weighted_revenue = fields.Monetary(currency_field="currency_id", readonly=True)
    revenue_at_risk = fields.Monetary(currency_field="currency_id", readonly=True)
    executive_summary_html = fields.Html(readonly=True)

    @api.depends("partner_id")
    def _compute_company_id(self):
        for pack in self:
            pack.company_id = pack.partner_id.company_id or self.env.company

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner = self.env["res.partner"].browse(vals.get("partner_id"))
            if partner and partner.commercial_partner_id:
                vals["partner_id"] = partner.commercial_partner_id.id
            if not vals.get("name") or vals.get("name") == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "helpdesk.service.review.pack"
                ) or _("New")
        packs = super().create(vals_list)
        for pack in packs:
            pack.action_generate_snapshot()
        return packs

    def _get_period_bounds(self):
        self.ensure_one()
        start = datetime.combine(self.date_from, time.min)
        end = datetime.combine(self.date_to + timedelta(days=1), time.min)
        return fields.Datetime.to_string(start), fields.Datetime.to_string(end)

    def _build_executive_summary(self, snapshot):
        return _(
            "<p><strong>Executive Summary</strong></p>"
            "<p>During %(date_from)s to %(date_to)s, %(customer)s logged %(created)s new tickets and closed %(closed)s tickets. "
            "There are currently %(open)s open tickets, with %(overdue)s overdue and %(escalated)s escalated.</p>"
            "<p>Customer engagement recorded %(comms)s communications, %(dispatches)s dispatches, %(invoices)s invoices, "
            "and an average satisfaction score of %(rating).2f / 5.</p>"
            "<p>Commercial exposure shows %(renewals)s active renewal watch items, %(renewal_overdue)s overdue follow-ups, "
            "weighted renewal revenue of %(weighted)s, and revenue at risk of %(risk)s.</p>"
        ) % {
            "date_from": self.date_from,
            "date_to": self.date_to,
            "customer": self.partner_id.display_name,
            "created": snapshot["tickets_created_count"],
            "closed": snapshot["tickets_closed_count"],
            "open": snapshot["current_open_ticket_count"],
            "overdue": snapshot["current_overdue_ticket_count"],
            "escalated": snapshot["current_escalated_ticket_count"],
            "comms": snapshot["communication_count"],
            "dispatches": snapshot["dispatch_count"],
            "invoices": snapshot["invoice_count"],
            "rating": snapshot["avg_rating"],
            "renewals": snapshot["renewal_watch_count"],
            "renewal_overdue": snapshot["renewal_overdue_followup_count"],
            "weighted": self.currency_id.symbol and ("%s%s" % (self.currency_id.symbol, format(snapshot["renewal_weighted_revenue"], ",.2f"))) or format(snapshot["renewal_weighted_revenue"], ",.2f"),
            "risk": self.currency_id.symbol and ("%s%s" % (self.currency_id.symbol, format(snapshot["revenue_at_risk"], ",.2f"))) or format(snapshot["revenue_at_risk"], ",.2f"),
        }

    def _prepare_snapshot_vals(self):
        self.ensure_one()
        root = self.partner_id.commercial_partner_id or self.partner_id
        ticket_model = self.env["helpdesk.ticket"].sudo()
        contract_model = self.env["helpdesk.support.contract"].sudo()
        approval_model = self.env["helpdesk.ticket.approval"].sudo()
        dispatch_model = self.env["helpdesk.dispatch"].sudo()
        communication_model = self.env["helpdesk.communication.log"].sudo()
        renewal_model = self.env["helpdesk.contract.renewal"].sudo()

        start_dt, end_dt = self._get_period_bounds()
        tickets = ticket_model.search([("commercial_partner_id", "=", root.id)])
        period_created = tickets.filtered(
            lambda ticket: ticket.create_date
            and self.date_from <= fields.Datetime.to_datetime(ticket.create_date).date() <= self.date_to
        )
        period_closed = tickets.filtered(
            lambda ticket: ticket.closed_date
            and self.date_from <= fields.Datetime.to_datetime(ticket.closed_date).date() <= self.date_to
        )
        open_tickets = tickets.filtered(lambda ticket: not ticket.closed)
        overdue_tickets = open_tickets.filtered("sla_expired")
        escalated_tickets = open_tickets.filtered("escalated")
        unassigned_tickets = open_tickets.filtered(lambda ticket: not ticket.user_id)
        ratings = tickets.mapped("rating_ids").filtered(
            lambda rating: rating.consumed
            and rating.rating
            and rating.create_date
            and self.date_from <= fields.Datetime.to_datetime(rating.create_date).date() <= self.date_to
        )
        resolution_hours = []
        for ticket in period_closed:
            if ticket.create_date and ticket.closed_date:
                resolution_hours.append(
                    (fields.Datetime.to_datetime(ticket.closed_date) - fields.Datetime.to_datetime(ticket.create_date)).total_seconds() / 3600.0
                )

        communications = communication_model.search(
            [
                ("ticket_id.commercial_partner_id", "=", root.id),
                ("logged_at", ">=", start_dt),
                ("logged_at", "<", end_dt),
            ]
        )
        dispatches = dispatch_model.search([("ticket_id.commercial_partner_id", "=", root.id)])
        period_dispatches = dispatches.filtered(
            lambda dispatch: dispatch.scheduled_start
            and self.date_from <= fields.Datetime.to_datetime(dispatch.scheduled_start).date() <= self.date_to
        )
        completed_dispatches = period_dispatches.filtered(lambda dispatch: dispatch.state == "completed")
        approvals = approval_model.search([("ticket_id.commercial_partner_id", "=", root.id)])
        pending_approvals = approvals.filtered(
            lambda approval: approval.state in {"requested", "in_review", "approved"}
        )
        contracts = contract_model.search([("partner_id", "=", root.id)])
        active_contracts = contracts.filtered(lambda contract: contract.state in {"active", "expiring"})
        invoices = tickets.mapped("invoice_ids").filtered(
            lambda move: move.move_type == "out_invoice"
            and move.state != "cancel"
            and move.invoice_date
            and self.date_from <= move.invoice_date <= self.date_to
        )
        renewals = renewal_model.search([("partner_id", "=", root.id)])
        active_renewals = renewals.filtered(
            lambda renewal: renewal.state in {"open", "in_review", "handoff_sent"}
        )

        if overdue_tickets or escalated_tickets:
            health = "critical"
        elif pending_approvals or period_dispatches.filtered(lambda dispatch: dispatch.state in {"scheduled", "en_route", "on_site"}) or unassigned_tickets:
            health = "attention"
        elif tickets or active_contracts:
            health = "stable"
        else:
            health = "quiet"

        if active_renewals.filtered(lambda renewal: renewal.risk_level == "critical" or renewal.follow_up_overdue):
            renewal_risk = "critical"
        elif active_renewals.filtered(lambda renewal: renewal.risk_level in {"high", "critical"}):
            renewal_risk = "at_risk"
        elif active_renewals:
            renewal_risk = "watch"
        else:
            renewal_risk = "stable"

        snapshot = {
            "prepared_at": fields.Datetime.now(),
            "prepared_by_id": self.env.user.id,
            "state": "generated",
            "health": health,
            "renewal_risk_segment": renewal_risk,
            "tickets_created_count": len(period_created),
            "tickets_closed_count": len(period_closed),
            "current_open_ticket_count": len(open_tickets),
            "current_overdue_ticket_count": len(overdue_tickets),
            "current_escalated_ticket_count": len(escalated_tickets),
            "current_unassigned_ticket_count": len(unassigned_tickets),
            "avg_resolution_hours": round(sum(resolution_hours) / len(resolution_hours), 2) if resolution_hours else 0.0,
            "avg_rating": round(sum(ratings.mapped("rating")) / len(ratings), 2) if ratings else 0.0,
            "portal_views_total": sum(tickets.mapped("public_portal_view_count")),
            "communication_count": len(communications),
            "inbound_communication_count": len(communications.filtered(lambda log: log.direction == "inbound")),
            "outbound_communication_count": len(communications.filtered(lambda log: log.direction == "outbound")),
            "failed_communication_count": len(communications.filtered(lambda log: log.status == "failed")),
            "dispatch_count": len(period_dispatches),
            "completed_dispatch_count": len(completed_dispatches),
            "pending_approval_count": len(pending_approvals),
            "active_contract_count": len(active_contracts),
            "contract_consumed_hours": sum(active_contracts.mapped("consumed_hours")),
            "contract_remaining_hours": sum(active_contracts.mapped("remaining_hours")),
            "uninvoiced_hours": sum(tickets.mapped("uninvoiced_billable_hours")),
            "invoice_count": len(invoices),
            "invoiced_amount": sum(invoices.mapped("amount_total")),
            "renewal_watch_count": len(active_renewals),
            "renewal_overdue_followup_count": len(active_renewals.filtered("follow_up_overdue")),
            "renewal_weighted_revenue": sum(active_renewals.mapped("weighted_revenue")),
            "revenue_at_risk": sum(active_renewals.mapped("revenue_at_risk")),
        }
        snapshot["executive_summary_html"] = self._build_executive_summary(snapshot)
        return snapshot

    def action_generate_snapshot(self):
        for pack in self:
            pack.write(pack._prepare_snapshot_vals())
        return True

    def action_print_pack(self):
        self.ensure_one()
        return self.env.ref(
            "helpdesk_custom_service_review_pack.action_report_helpdesk_service_review_pack"
        ).report_action(self)

    def action_open_customer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer"),
            "res_model": "res.partner",
            "view_mode": "form",
            "res_id": self.partner_id.id,
        }

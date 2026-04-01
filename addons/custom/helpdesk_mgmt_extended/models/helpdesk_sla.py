# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import api, fields, models


class HelpdeskSla(models.Model):
    _name = "helpdesk.sla"
    _description = "Helpdesk SLA Policy"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_sla_team_rel",
        "sla_id",
        "team_id",
        string="Teams",
    )
    category_ids = fields.Many2many(
        "helpdesk.ticket.category",
        "helpdesk_sla_category_rel",
        "sla_id",
        "category_id",
        string="Categories",
    )
    tag_ids = fields.Many2many(
        "helpdesk.ticket.tag",
        "helpdesk_sla_tag_rel",
        "sla_id",
        "tag_id",
        string="Tags",
    )
    stage_ids = fields.Many2many(
        "helpdesk.ticket.stage",
        "helpdesk_sla_stage_rel",
        "sla_id",
        "stage_id",
        string="Target Stages",
        help="SLA is met when the ticket reaches one of these stages.",
    )
    days = fields.Integer(string="Days", default=0)
    hours = fields.Integer(string="Hours", default=8)
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Urgent")],
        string="Minimum Priority",
        default="0",
    )
    domain = fields.Char(
        string="Extra Filter",
        default="[]",
        help="Optional domain to further restrict which tickets this SLA applies to.",
    )

    # ── Applicability ─────────────────────────────────────────────────────────

    def _applies_for(self, ticket):
        """Return True if this SLA policy applies to the given ticket."""
        self.ensure_one()
        # Team filter
        if self.team_ids and ticket.team_id not in self.team_ids:
            return False
        # Category filter
        if self.category_ids and ticket.category_id not in self.category_ids:
            return False
        # Tag filter
        if self.tag_ids and not (set(ticket.tag_ids.ids) & set(self.tag_ids.ids)):
            return False
        # Priority filter
        if self.priority and (ticket.priority or "0") < self.priority:
            return False
        # Extra domain filter
        if self.domain and self.domain.strip() not in ("[]", ""):
            try:
                import ast
                extra_domain = ast.literal_eval(self.domain)
                if extra_domain:
                    match = self.env["helpdesk.ticket"].search_count(
                        [("id", "=", ticket.id)] + extra_domain
                    )
                    if not match:
                        return False
            except Exception:
                pass
        return True

    # ── Deadline calculation ──────────────────────────────────────────────────

    def _compute_deadline(self, ticket):
        """Return the SLA deadline datetime for the given ticket."""
        self.ensure_one()
        calendar = ticket.team_id.resource_calendar_id
        start = ticket.create_date or fields.Datetime.now()
        if calendar:
            # Use working-hours calendar
            dt = calendar.plan_hours(self.days * 24 + self.hours, start)
        else:
            dt = start + timedelta(days=self.days, hours=self.hours)
        return dt

    # ── Cron ──────────────────────────────────────────────────────────────────

    @api.model
    def _cron_check_sla(self):
        """Called by the scheduled action to flag expired SLA tickets."""
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.core.extended"):
            return
        open_tickets = self.env["helpdesk.ticket"].search(
            [("closed", "=", False)]
        )
        for ticket in open_tickets:
            ticket._check_ticket_sla()

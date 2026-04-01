# -*- coding: utf-8 -*-
import random

from odoo import api, fields, models


class HelpdeskTicketTeam(models.Model):
    """Extend the base team with all sub-module settings consolidated."""
    _inherit = "helpdesk.ticket.team"

    # ── SLA (helpdesk_mgmt_sla) ───────────────────────────────────────────────
    use_sla = fields.Boolean(string="Use SLA Policies", default=False)
    resource_calendar_id = fields.Many2one(
        "resource.calendar",
        string="Working Hours",
        help="Used to compute SLA deadlines based on business hours.",
    )
    # ── Types (helpdesk_type) ─────────────────────────────────────────────────
    type_ids = fields.Many2many(
        "helpdesk.ticket.type",
        "helpdesk_type_team_rel",
        "team_id",
        "type_id",
        string="Ticket Types",
    )

    # ── Auto-Assignment (helpdesk_mgmt_assign_method) ─────────────────────────
    assign_method = fields.Selection(
        [
            ("manual", "Manual"),
            ("randomly", "Random"),
            ("balanced", "Balanced (least tickets)"),
            ("sequential", "Sequential (round-robin)"),
        ],
        string="Assignment Method",
        default="manual",
    )
    # Internal pointer for round-robin
    _sequential_index = 0

    def get_new_user(self):
        """Return the user to assign to a new ticket based on assign_method."""
        self.ensure_one()
        if self.assign_method == "randomly":
            return self._assign_randomly()
        elif self.assign_method == "balanced":
            return self._assign_balanced()
        elif self.assign_method == "sequential":
            return self._assign_sequential()
        return self.env["res.users"]

    def _assign_randomly(self):
        members = self.member_ids
        return random.choice(members) if members else self.env["res.users"]

    def _assign_balanced(self):
        members = self.member_ids
        if not members:
            return self.env["res.users"]
        ticket_counts = {
            u.id: self.env["helpdesk.ticket"].search_count(
                [("user_id", "=", u.id), ("closed", "=", False)]
            )
            for u in members
        }
        min_user_id = min(ticket_counts, key=ticket_counts.get)
        return self.env["res.users"].browse(min_user_id)

    def _assign_sequential(self):
        members = list(self.member_ids)
        if not members:
            return self.env["res.users"]
        idx = HelpdeskTicketTeam._sequential_index % len(members)
        HelpdeskTicketTeam._sequential_index += 1
        return members[idx]

    # ── Close Inactive (helpdesk_ticket_close_inactive) ───────────────────────
    close_inactive_tickets = fields.Boolean(
        string="Auto-Close Inactive Tickets",
        default=False,
    )
    inactivity_warning_days = fields.Integer(
        string="Warning After (days)",
        default=5,
        help="Send a warning email to the customer after this many days of inactivity.",
    )
    inactivity_close_days = fields.Integer(
        string="Close After (days)",
        default=10,
        help="Close the ticket after this many days of inactivity.",
    )
    inactivity_warning_template_id = fields.Many2one(
        "mail.template",
        string="Warning Email Template",
        domain=[("model", "=", "helpdesk.ticket")],
    )
    inactivity_closing_template_id = fields.Many2one(
        "mail.template",
        string="Closing Email Template",
        domain=[("model", "=", "helpdesk.ticket")],
    )
    closing_ticket_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Stage on Auto-Close",
    )

    def close_team_inactive_tickets(self):
        """Close or warn about tickets that have been inactive."""
        self.ensure_one()
        if not self.close_inactive_tickets:
            return
        now = fields.Datetime.now()
        open_tickets = self.env["helpdesk.ticket"].search(
            [("team_id", "=", self.id), ("closed", "=", False)]
        )
        for ticket in open_tickets:
            last_activity = ticket.write_date or ticket.create_date
            delta = (now - last_activity).days
            if delta >= self.inactivity_close_days:
                vals = {}
                if self.closing_ticket_stage_id:
                    vals["stage_id"] = self.closing_ticket_stage_id.id
                else:
                    vals["closed"] = True
                if self.inactivity_closing_template_id:
                    self.inactivity_closing_template_id.send_mail(ticket.id, force_send=True)
                ticket.write(vals)
            elif delta >= self.inactivity_warning_days:
                if self.inactivity_warning_template_id:
                    self.inactivity_warning_template_id.send_mail(ticket.id, force_send=True)

    # ── Project (helpdesk_mgmt_project) ───────────────────────────────────────
    default_project_id = fields.Many2one(
        "project.project",
        string="Default Project",
        help="Tickets in this team will be linked to this project by default.",
    )

    # ── Timesheet (helpdesk_mgmt_timesheet) ───────────────────────────────────
    allow_timesheet = fields.Boolean(
        string="Allow Timesheets",
        default=False,
        help="Allow team members to log time directly on tickets.",
    )

    # ── Portal Restriction (helpdesk_portal_restriction) ─────────────────────
    helpdesk_partner_ids = fields.Many2many(
        "res.partner",
        "helpdesk_team_partner_rel",
        "team_id",
        "partner_id",
        string="Allowed Portal Users",
        help="Restrict portal visibility to these partners. Leave empty to allow all.",
    )

    # ── Auto-Update Stage on Customer Reply (helpdesk_ticket_partner_response) ─
    autoupdate_ticket_stage = fields.Boolean(
        string="Auto-Update Stage on Customer Reply",
        default=False,
    )
    autopupdate_src_stage_ids = fields.Many2many(
        "helpdesk.ticket.stage",
        "helpdesk_team_src_stage_rel",
        "team_id",
        "stage_id",
        string="Source Stages",
        help="Move ticket from these stages when the customer replies.",
    )
    autopupdate_dest_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Destination Stage",
        help="Stage to move the ticket to when the customer replies.",
    )

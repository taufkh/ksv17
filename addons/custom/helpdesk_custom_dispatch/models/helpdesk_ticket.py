from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def _ensure_dispatch_feature_enabled(self):
        self.ensure_one()
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.ops.dispatch",
            message=_("Helpdesk dispatch is disabled in Helpdesk feature settings."),
        )
        return True

    dispatch_ids = fields.One2many(
        "helpdesk.dispatch",
        "ticket_id",
        string="Dispatches",
    )
    dispatch_count = fields.Integer(
        compute="_compute_dispatch_summary",
        store=True,
        compute_sudo=True,
    )
    next_dispatch_start = fields.Datetime(
        compute="_compute_dispatch_summary",
        store=True,
        compute_sudo=True,
    )
    latest_dispatch_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("scheduled", "Scheduled"),
            ("en_route", "En Route"),
            ("on_site", "On Site"),
            ("completed", "Completed"),
            ("no_access", "No Access"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_dispatch_summary",
        store=True,
        compute_sudo=True,
    )

    @api.depends("dispatch_ids", "dispatch_ids.state", "dispatch_ids.scheduled_start")
    def _compute_dispatch_summary(self):
        for ticket in self:
            dispatches = ticket.dispatch_ids.sorted(
                key=lambda dispatch: dispatch.scheduled_start or fields.Datetime.now(),
                reverse=True,
            )
            ticket.dispatch_count = len(dispatches)
            ticket.latest_dispatch_state = dispatches[:1].state if dispatches else False
            upcoming = dispatches.filtered(
                lambda dispatch: dispatch.state in {"draft", "scheduled", "en_route", "on_site"}
            ).sorted(key=lambda dispatch: dispatch.scheduled_start or fields.Datetime.now())
            ticket.next_dispatch_start = upcoming[:1].scheduled_start if upcoming else False

    def _default_dispatch_approval(self):
        self.ensure_one()
        approval = self.env["helpdesk.ticket.approval"].search(
            [
                ("ticket_id", "=", self.id),
                ("approval_type", "=", "onsite_visit"),
                ("state", "in", ["requested", "in_review", "approved"]),
            ],
            order="required_by_date asc, id desc",
            limit=1,
        )
        return approval

    def action_schedule_dispatch(self):
        self.ensure_one()
        self._ensure_dispatch_feature_enabled()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_dispatch.action_helpdesk_dispatch"
        )
        action["views"] = [
            (
                self.env.ref("helpdesk_custom_dispatch.view_helpdesk_dispatch_form").id,
                "form",
            )
        ]
        approval = self._default_dispatch_approval()
        action["context"] = {
            "default_ticket_id": self.id,
            "default_engineer_id": self.user_id.id or self.env.user.id,
            "default_site_contact_name": self.partner_name or self.partner_id.name,
            "default_site_contact_phone": self.partner_id.phone or self.partner_id.mobile,
            "default_location": self.partner_id.contact_address_complete or self.partner_name,
            "default_work_summary": _("<p>Planned dispatch created from helpdesk ticket.</p>"),
            "default_approval_id": approval.id,
        }
        return action

    def action_open_dispatches(self):
        self.ensure_one()
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.ops.dispatch"):
            raise UserError(_("Helpdesk dispatch is disabled in Helpdesk feature settings."))
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_dispatch.action_helpdesk_dispatch"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {
            "default_ticket_id": self.id,
            "search_default_ticket_id": self.id,
        }
        return action

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HelpdeskDispatch(models.Model):
    _name = "helpdesk.dispatch"
    _description = "Helpdesk Dispatch"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "scheduled_start desc, id desc"

    state_selection = [
        ("draft", "Draft"),
        ("scheduled", "Scheduled"),
        ("en_route", "En Route"),
        ("on_site", "On Site"),
        ("completed", "Completed"),
        ("no_access", "No Access"),
        ("cancelled", "Cancelled"),
    ]
    dispatch_type_selection = [
        ("onsite_visit", "Onsite Visit"),
        ("remote_session", "Remote Session"),
        ("inspection", "Inspection"),
        ("delivery", "Delivery / Replacement"),
    ]
    urgency_selection = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    resolution_status_selection = [
        ("pending", "Pending"),
        ("temporary_fix", "Temporary Fix"),
        ("resolved", "Resolved"),
        ("follow_up", "Follow-up Required"),
    ]

    name = fields.Char(required=True, tracking=True, default="New Dispatch")
    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    partner_id = fields.Many2one(related="ticket_id.partner_id", store=True, readonly=True)
    company_id = fields.Many2one(related="ticket_id.company_id", store=True, readonly=True)
    team_id = fields.Many2one(
        related="ticket_id.team_id",
        string="Helpdesk Team",
        store=True,
        readonly=True,
    )
    ticket_user_id = fields.Many2one(
        related="ticket_id.user_id",
        string="Ticket Owner",
        store=True,
        readonly=True,
    )
    project_id = fields.Many2one(related="ticket_id.project_id", store=True, readonly=True)
    task_id = fields.Many2one(related="ticket_id.task_id", store=True, readonly=True)
    approval_id = fields.Many2one(
        "helpdesk.ticket.approval",
        string="Related Approval",
        tracking=True,
        domain="[('ticket_id', '=', ticket_id)]",
    )
    engineer_id = fields.Many2one(
        "res.users",
        string="Engineer",
        required=True,
        tracking=True,
        domain=[("share", "=", False)],
    )
    dispatch_type = fields.Selection(
        selection=dispatch_type_selection,
        required=True,
        default="onsite_visit",
        tracking=True,
    )
    urgency = fields.Selection(
        selection=urgency_selection,
        required=True,
        default="normal",
        tracking=True,
    )
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="draft",
        tracking=True,
    )
    scheduled_start = fields.Datetime(required=True, tracking=True)
    scheduled_end = fields.Datetime(required=True, tracking=True)
    actual_start = fields.Datetime(tracking=True)
    actual_end = fields.Datetime(tracking=True)
    planned_hours = fields.Float(compute="_compute_hours", store=True)
    actual_hours = fields.Float(compute="_compute_hours", store=True)
    location = fields.Char(tracking=True)
    site_contact_name = fields.Char(string="Site Contact", tracking=True)
    site_contact_phone = fields.Char(string="Contact Phone", tracking=True)
    travel_required = fields.Boolean(default=True, tracking=True)
    resolution_status = fields.Selection(
        selection=resolution_status_selection,
        default="pending",
        tracking=True,
    )
    work_summary = fields.Html()
    visit_findings = fields.Html()
    followup_required = fields.Boolean(tracking=True)
    followup_action = fields.Text(tracking=True)
    calendar_color = fields.Integer(compute="_compute_calendar_color")

    @api.depends("scheduled_start", "scheduled_end", "actual_start", "actual_end")
    def _compute_hours(self):
        for dispatch in self:
            dispatch.planned_hours = 0.0
            dispatch.actual_hours = 0.0
            if dispatch.scheduled_start and dispatch.scheduled_end:
                start = fields.Datetime.to_datetime(dispatch.scheduled_start)
                end = fields.Datetime.to_datetime(dispatch.scheduled_end)
                dispatch.planned_hours = max((end - start).total_seconds() / 3600.0, 0.0)
            if dispatch.actual_start and dispatch.actual_end:
                start = fields.Datetime.to_datetime(dispatch.actual_start)
                end = fields.Datetime.to_datetime(dispatch.actual_end)
                dispatch.actual_hours = max((end - start).total_seconds() / 3600.0, 0.0)

    @api.depends("state")
    def _compute_calendar_color(self):
        color_map = {
            "draft": 0,
            "scheduled": 3,
            "en_route": 4,
            "on_site": 7,
            "completed": 10,
            "no_access": 2,
            "cancelled": 1,
        }
        for dispatch in self:
            dispatch.calendar_color = color_map.get(dispatch.state, 0)

    @api.onchange("ticket_id")
    def _onchange_ticket_id(self):
        for dispatch in self:
            if not dispatch.ticket_id:
                continue
            if not dispatch.engineer_id and dispatch.ticket_id.user_id:
                dispatch.engineer_id = dispatch.ticket_id.user_id
            if not dispatch.location:
                dispatch.location = dispatch.ticket_id.partner_id.contact_address_complete or dispatch.ticket_id.partner_name
            if not dispatch.site_contact_name:
                dispatch.site_contact_name = dispatch.ticket_id.partner_name or dispatch.ticket_id.partner_id.name
            if not dispatch.site_contact_phone:
                dispatch.site_contact_phone = dispatch.ticket_id.partner_id.phone or dispatch.ticket_id.partner_id.mobile
            if not dispatch.name or dispatch.name == "New Dispatch":
                dispatch.name = _("%(ticket)s Dispatch") % {"ticket": dispatch.ticket_id.number}

    @api.constrains("scheduled_start", "scheduled_end")
    def _check_schedule_window(self):
        for dispatch in self:
            if dispatch.scheduled_start and dispatch.scheduled_end and dispatch.scheduled_end < dispatch.scheduled_start:
                raise ValidationError(_("Scheduled end must be later than scheduled start."))

    def _close_pending_activities(self):
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        activities = self.activity_ids
        if todo:
            activities = activities.filtered(lambda act: act.activity_type_id == todo)
        activities.unlink()

    def _schedule_engineer_activity(self):
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not todo:
            return
        for dispatch in self.filtered("engineer_id"):
            dispatch.activity_schedule(
                activity_type_id=todo.id,
                user_id=dispatch.engineer_id.id,
                date_deadline=fields.Date.to_date(dispatch.scheduled_start) if dispatch.scheduled_start else fields.Date.context_today(dispatch),
                summary=_("Dispatch scheduled: %(name)s") % {"name": dispatch.display_name},
                note=dispatch.work_summary or dispatch.ticket_id.display_name,
            )

    def _post_ticket_message(self, body):
        for dispatch in self:
            dispatch.ticket_id.message_post(body=body % {"name": dispatch.display_name})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals.get("name") == "New Dispatch":
                ticket = self.env["helpdesk.ticket"].browse(vals.get("ticket_id"))
                vals["name"] = _("%(ticket)s Dispatch") % {
                    "ticket": ticket.number or ticket.name or _("Ticket")
                }
            if not vals.get("engineer_id") and vals.get("ticket_id"):
                ticket = self.env["helpdesk.ticket"].browse(vals["ticket_id"])
                vals["engineer_id"] = ticket.user_id.id or self.env.user.id
        return super().create(vals_list)

    def action_schedule(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"draft", "cancelled"}):
            dispatch.write({"state": "scheduled"})
            dispatch._schedule_engineer_activity()
            dispatch.message_post(body=_("Dispatch scheduled."))
            dispatch._post_ticket_message(_("Dispatch %(name)s has been scheduled."))
        return True

    def action_mark_en_route(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"scheduled", "draft"}):
            values = {"state": "en_route"}
            if not dispatch.actual_start:
                values["actual_start"] = fields.Datetime.now()
            dispatch.write(values)
            dispatch.message_post(body=_("Engineer is now en route."))
            dispatch._post_ticket_message(_("Dispatch %(name)s is now en route."))
        return True

    def action_check_in(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"scheduled", "en_route", "draft"}):
            values = {"state": "on_site"}
            if not dispatch.actual_start:
                values["actual_start"] = fields.Datetime.now()
            dispatch.write(values)
            dispatch.message_post(body=_("Engineer checked in on site."))
            dispatch._post_ticket_message(_("Dispatch %(name)s is now on site."))
        return True

    def action_complete(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"scheduled", "en_route", "on_site"}):
            values = {
                "state": "completed",
                "actual_end": dispatch.actual_end or fields.Datetime.now(),
            }
            if not dispatch.actual_start:
                values["actual_start"] = dispatch.scheduled_start or fields.Datetime.now()
            if not dispatch.resolution_status or dispatch.resolution_status == "pending":
                values["resolution_status"] = "resolved" if not dispatch.followup_required else "follow_up"
            dispatch.write(values)
            dispatch._close_pending_activities()
            if (
                dispatch.approval_id
                and dispatch.approval_id.approval_type == "onsite_visit"
                and dispatch.approval_id.state == "approved"
            ):
                dispatch.approval_id.action_mark_implemented()
            dispatch.message_post(body=_("Dispatch completed."))
            dispatch._post_ticket_message(_("Dispatch %(name)s has been completed."))
        return True

    def action_mark_no_access(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"scheduled", "en_route", "on_site"}):
            values = {
                "state": "no_access",
                "actual_end": fields.Datetime.now(),
                "resolution_status": "follow_up",
                "followup_required": True,
            }
            if not dispatch.actual_start:
                values["actual_start"] = fields.Datetime.now()
            dispatch.write(values)
            dispatch._close_pending_activities()
            dispatch.message_post(body=_("Dispatch ended with no site access."))
            dispatch._post_ticket_message(_("Dispatch %(name)s could not proceed because site access was unavailable."))
        return True

    def action_cancel(self):
        for dispatch in self.filtered(lambda rec: rec.state in {"draft", "scheduled", "en_route", "on_site"}):
            dispatch.write({"state": "cancelled"})
            dispatch._close_pending_activities()
            dispatch.message_post(body=_("Dispatch cancelled."))
            dispatch._post_ticket_message(_("Dispatch %(name)s has been cancelled."))
        return True

    def action_reset_draft(self):
        for dispatch in self:
            dispatch.write({"state": "draft"})
            dispatch.message_post(body=_("Dispatch reset to draft."))
        return True

    def action_open_ticket(self):
        self.ensure_one()
        return self.ticket_id.get_formview_action()

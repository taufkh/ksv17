from odoo import _, api, fields, models


class HelpdeskTicketApproval(models.Model):
    _name = "helpdesk.ticket.approval"
    _description = "Helpdesk Ticket Approval"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "request_date desc, id desc"

    state_selection = [
        ("draft", "Draft"),
        ("requested", "Requested"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("implemented", "Implemented"),
        ("cancelled", "Cancelled"),
    ]

    approval_type_selection = [
        ("refund", "Refund"),
        ("onsite_visit", "Onsite Visit"),
        ("replacement", "Replacement Unit"),
        ("billing_exception", "Billing Exception"),
        ("sla_waiver", "SLA Waiver"),
        ("access_exception", "Access Exception"),
        ("custom", "Other"),
    ]

    urgency_selection = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    default_name = "New Approval Request"

    name = fields.Char(required=True, tracking=True, default=default_name)
    ticket_id = fields.Many2one(
        comodel_name="helpdesk.ticket",
        string="Ticket",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    partner_id = fields.Many2one(
        related="ticket_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="ticket_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )
    helpdesk_team_id = fields.Many2one(
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
    requester_id = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    approver_id = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        required=True,
        domain=[("share", "=", False)],
        tracking=True,
    )
    approval_type = fields.Selection(
        selection=approval_type_selection,
        required=True,
        default="custom",
        tracking=True,
    )
    urgency = fields.Selection(
        selection=urgency_selection,
        required=True,
        default="normal",
        tracking=True,
    )
    requested_amount = fields.Monetary(string="Requested Amount", tracking=True)
    required_by_date = fields.Date(string="Needed By", tracking=True)
    justification = fields.Html(required=True)
    customer_impact = fields.Html()
    decision_note = fields.Text(tracking=True)
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="draft",
        tracking=True,
    )
    request_date = fields.Datetime(readonly=True, tracking=True)
    review_date = fields.Datetime(readonly=True, tracking=True)
    decision_date = fields.Datetime(readonly=True, tracking=True)
    implemented_date = fields.Datetime(readonly=True, tracking=True)
    decision_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Decision By",
        readonly=True,
        tracking=True,
    )
    implemented_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Implemented By",
        readonly=True,
        tracking=True,
    )

    def _selection_label(self, field_name, value):
        field = self._fields[field_name]
        return dict(field.selection).get(value, value)

    def _default_name_from_ticket(self):
        self.ensure_one()
        return _("%(ticket)s - %(approval)s Approval") % {
            "ticket": self.ticket_id.number,
            "approval": self._selection_label("approval_type", self.approval_type),
        }

    def _close_pending_activities(self):
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        activities = self.activity_ids
        if todo:
            activities = activities.filtered(lambda act: act.activity_type_id == todo)
        activities.unlink()

    def _schedule_review_activity(self):
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not todo or not self.approver_id:
            return
        self.activity_schedule(
            activity_type_id=todo.id,
            user_id=self.approver_id.id,
            date_deadline=self.required_by_date or fields.Date.context_today(self),
            summary=_("Review helpdesk approval: %(name)s") % {"name": self.display_name},
            note=self.justification or self.name,
        )

    def _post_ticket_update(self, message):
        for approval in self:
            approval.ticket_id.message_post(body=message % {"name": approval.display_name})

    def action_submit(self):
        for approval in self.filtered(lambda record: record.state in {"draft", "cancelled"}):
            approval.write(
                {
                    "state": "requested",
                    "request_date": fields.Datetime.now(),
                }
            )
            approval._schedule_review_activity()
            approval.message_post(body=_("Approval request submitted for review."))
            approval.ticket_id.message_post(
                body=_("Approval request %(name)s submitted.") % {"name": approval.display_name}
            )
        return True

    def action_mark_in_review(self):
        for approval in self.filtered(lambda record: record.state in {"requested", "approved"}):
            approval.write(
                {
                    "state": "in_review",
                    "review_date": fields.Datetime.now(),
                }
            )
            approval.message_post(body=_("Approval request is now under review."))
            approval.ticket_id.message_post(
                body=_("Approval request %(name)s is now under review.")
                % {"name": approval.display_name}
            )
        return True

    def action_approve(self):
        for approval in self.filtered(lambda record: record.state in {"requested", "in_review"}):
            approval.write(
                {
                    "state": "approved",
                    "review_date": approval.review_date or fields.Datetime.now(),
                    "decision_date": fields.Datetime.now(),
                    "decision_by_id": self.env.user.id,
                }
            )
            approval._close_pending_activities()
            approval.message_post(body=_("Approval request approved."))
            approval.ticket_id.message_post(
                body=_("Approval request %(name)s has been approved.")
                % {"name": approval.display_name}
            )
        return True

    def action_reject(self):
        for approval in self.filtered(lambda record: record.state in {"requested", "in_review", "approved"}):
            approval.write(
                {
                    "state": "rejected",
                    "review_date": approval.review_date or fields.Datetime.now(),
                    "decision_date": fields.Datetime.now(),
                    "decision_by_id": self.env.user.id,
                }
            )
            approval._close_pending_activities()
            approval.message_post(body=_("Approval request rejected."))
            approval.ticket_id.message_post(
                body=_("Approval request %(name)s has been rejected.")
                % {"name": approval.display_name}
            )
        return True

    def action_mark_implemented(self):
        for approval in self.filtered(lambda record: record.state == "approved"):
            approval.write(
                {
                    "state": "implemented",
                    "implemented_date": fields.Datetime.now(),
                    "implemented_by_id": self.env.user.id,
                }
            )
            approval.message_post(body=_("Approved action has been implemented."))
            approval.ticket_id.message_post(
                body=_("Approved action for %(name)s has been implemented.")
                % {"name": approval.display_name}
            )
        return True

    def action_cancel(self):
        for approval in self.filtered(lambda record: record.state in {"draft", "requested", "in_review"}):
            approval.write({"state": "cancelled"})
            approval._close_pending_activities()
            approval.message_post(body=_("Approval request cancelled."))
        return True

    def action_open_ticket(self):
        self.ensure_one()
        return self.ticket_id.get_formview_action()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if (not record.name or record.name == self.default_name) and record.ticket_id:
                record.name = record._default_name_from_ticket()
            if record.state == "requested" and not record.request_date:
                record.request_date = fields.Datetime.now()
            if record.state in {"requested", "in_review"}:
                record._schedule_review_activity()
            record.ticket_id.message_post(
                body=_("Approval request %(name)s created.") % {"name": record.display_name}
            )
        return records

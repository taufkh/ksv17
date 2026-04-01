from odoo import _, api, fields, models


class HelpdeskSalesHandoff(models.Model):
    _name = "helpdesk.sales.handoff"
    _description = "Helpdesk Sales Handoff"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc, id desc"

    state_selection = [
        ("draft", "Draft"),
        ("requested", "Requested"),
        ("in_review", "In Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("converted", "Converted"),
    ]

    reason_selection = [
        ("upsell", "Upsell"),
        ("renewal", "Renewal"),
        ("new_project", "New Project"),
        ("quotation", "Quotation Request"),
        ("commercial_issue", "Commercial Follow-up"),
        ("other", "Other"),
    ]

    urgency_selection = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    name = fields.Char(required=True, tracking=True)
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
        store=True,
        readonly=True,
        string="Helpdesk Team",
    )
    helpdesk_user_id = fields.Many2one(
        related="ticket_id.user_id",
        store=True,
        readonly=True,
        string="Ticket Owner",
    )
    requester_id = fields.Many2one(
        comodel_name="res.users",
        string="Requested By",
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )
    sales_team_id = fields.Many2one(
        comodel_name="crm.team",
        string="Sales Team",
        tracking=True,
    )
    sales_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Salesperson",
        tracking=True,
    )
    reason = fields.Selection(
        selection=reason_selection,
        required=True,
        default="upsell",
        tracking=True,
    )
    urgency = fields.Selection(
        selection=urgency_selection,
        required=True,
        default="normal",
        tracking=True,
    )
    expected_revenue = fields.Monetary(tracking=True)
    note = fields.Html(string="Sales Context", required=True)
    decision_note = fields.Text(tracking=True)
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="requested",
        tracking=True,
    )
    request_date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
        tracking=True,
    )
    review_date = fields.Datetime(readonly=True, tracking=True)
    rejected_date = fields.Datetime(readonly=True, tracking=True)
    converted_date = fields.Datetime(readonly=True, tracking=True)
    lead_id = fields.Many2one(
        comodel_name="crm.lead",
        string="Opportunity",
        copy=False,
        readonly=True,
        tracking=True,
    )

    def _default_name_from_ticket(self):
        self.ensure_one()
        return _("%(ticket)s - Sales Follow-up") % {"ticket": self.ticket_id.number}

    def action_submit(self):
        for handoff in self.filtered(lambda item: item.state == "draft"):
            handoff.write({"state": "requested", "request_date": fields.Datetime.now()})
            handoff.message_post(body=_("Sales handoff submitted for review."))
        return True

    def action_mark_in_review(self):
        for handoff in self.filtered(
            lambda item: item.state in {"requested", "approved"}
        ):
            handoff.write(
                {
                    "state": "in_review",
                    "review_date": fields.Datetime.now(),
                }
            )
            handoff.message_post(body=_("Sales handoff is now under review."))
        return True

    def action_approve(self):
        for handoff in self.filtered(
            lambda item: item.state in {"requested", "in_review"}
        ):
            handoff.write(
                {
                    "state": "approved",
                    "review_date": fields.Datetime.now(),
                }
            )
            handoff.message_post(body=_("Sales handoff approved and ready for conversion."))
        return True

    def action_reject(self):
        for handoff in self.filtered(
            lambda item: item.state in {"requested", "in_review", "approved"}
        ):
            handoff.write(
                {
                    "state": "rejected",
                    "rejected_date": fields.Datetime.now(),
                }
            )
            handoff.message_post(body=_("Sales handoff was rejected."))
        return True

    def action_convert_to_opportunity(self):
        self.ensure_one()
        wizard = (
            self.env["helpdesk.ticket.create.lead"]
            .with_context(active_id=self.ticket_id.id)
            .create(
                {
                    "ticket_id": self.ticket_id.id,
                    "user_id": self.sales_user_id.id or self.ticket_id.user_id.id,
                    "team_id": self.sales_team_id.id,
                }
            )
        )
        action = wizard.action_helpdesk_ticket_to_lead()
        lead = self.env["crm.lead"].browse(action.get("res_id"))
        lead_values = {"sales_handoff_id": self.id}
        if self.name:
            lead_values["name"] = self.name
        if self.sales_user_id:
            lead_values["user_id"] = self.sales_user_id.id
        if self.sales_team_id:
            lead_values["team_id"] = self.sales_team_id.id
        if self.expected_revenue:
            lead_values["expected_revenue"] = self.expected_revenue
        lead.write(lead_values)
        if self.note:
            lead.message_post(body=self.note, subject=_("Sales handoff context"))
        self.write(
            {
                "lead_id": lead.id,
                "state": "converted",
                "converted_date": fields.Datetime.now(),
            }
        )
        self.ticket_id.message_post(
            body=_("Sales handoff converted to opportunity %(name)s.")
            % {"name": lead.display_name}
        )
        return action

    def action_open_ticket(self):
        self.ensure_one()
        return self.ticket_id.get_formview_action()

    def action_open_opportunity(self):
        self.ensure_one()
        if not self.lead_id:
            return False
        return self.lead_id.get_formview_action()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.name and record.ticket_id:
                record.name = record._default_name_from_ticket()
            record.ticket_id.message_post(
                body=_("Sales handoff %(name)s created for sales review.")
                % {"name": record.display_name}
            )
        return records

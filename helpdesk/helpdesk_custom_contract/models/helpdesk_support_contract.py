from odoo import _, api, fields, models


class HelpdeskSupportContract(models.Model):
    _name = "helpdesk.support.contract"
    _description = "Helpdesk Support Contract"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, end_date desc, id desc"

    contract_type_selection = [
        ("retainer", "Retainer"),
        ("block", "Block Hours"),
        ("incident", "Incident Bundle"),
        ("warranty", "Warranty"),
    ]
    manual_state_selection = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
    ]
    state_selection = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("expiring", "Expiring"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
        ("cancelled", "Cancelled"),
    ]
    sla_tier_selection = [
        ("standard", "Standard"),
        ("premium", "Premium"),
        ("critical", "Critical"),
    ]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        domain=[("is_company", "=", True)],
        tracking=True,
    )
    company_id = fields.Many2one(
        related="partner_id.company_id",
        readonly=True,
        store=True,
    )
    team_id = fields.Many2one("helpdesk.ticket.team", string="Helpdesk Team", tracking=True)
    contract_type = fields.Selection(
        selection=contract_type_selection,
        required=True,
        default="retainer",
        tracking=True,
        help=(
            "Retainer: recurring support coverage with a monthly or periodic hour allowance.\n"
            "Block Hours: prepaid support hours consumed until the purchased balance is exhausted.\n"
            "Incident Bundle: support entitlement based on a fixed number of incidents rather than time.\n"
            "Warranty: issue resolution covered under product or implementation warranty terms."
        ),
    )
    sla_tier = fields.Selection(
        selection=sla_tier_selection,
        required=True,
        default="standard",
        tracking=True,
    )
    manual_state = fields.Selection(
        selection=manual_state_selection,
        required=True,
        default="draft",
        tracking=True,
    )
    state = fields.Selection(
        selection=state_selection,
        compute="_compute_state",
        store=True,
        tracking=True,
    )
    start_date = fields.Date(required=True, tracking=True)
    end_date = fields.Date(required=True, tracking=True)
    included_hours = fields.Float(tracking=True)
    warning_hours = fields.Float(default=2.0, tracking=True)
    allow_overrun = fields.Boolean(default=False, tracking=True)
    notes = fields.Html()
    ticket_ids = fields.One2many(
        "helpdesk.ticket",
        "support_contract_id",
        string="Tickets",
    )
    active_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    covered_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    consumed_hours = fields.Float(compute="_compute_metrics", store=True)
    remaining_hours = fields.Float(compute="_compute_metrics", store=True)
    overrun_hours = fields.Float(compute="_compute_metrics", store=True)
    utilization_rate = fields.Float(compute="_compute_metrics", store=True)

    @api.depends("manual_state", "start_date", "end_date")
    def _compute_state(self):
        today = fields.Date.today()
        for contract in self:
            if contract.manual_state in {"suspended", "cancelled"}:
                contract.state = contract.manual_state
            elif not contract.start_date or not contract.end_date:
                contract.state = "draft"
            elif contract.manual_state == "draft":
                contract.state = "draft"
            elif contract.end_date < today:
                contract.state = "expired"
            elif contract.end_date <= fields.Date.add(today, days=7):
                contract.state = "expiring"
            else:
                contract.state = "active"

    @api.depends(
        "ticket_ids.stage_id",
        "ticket_ids.total_hours",
        "ticket_ids.timesheet_ids.unit_amount",
        "ticket_ids.timesheet_ids.date",
        "ticket_ids.create_date",
        "included_hours",
    )
    def _compute_metrics(self):
        for contract in self:
            lines = contract.ticket_ids.mapped("timesheet_ids")
            if contract.start_date:
                lines = lines.filtered(lambda line: not line.date or line.date >= contract.start_date)
            if contract.end_date:
                lines = lines.filtered(lambda line: not line.date or line.date <= contract.end_date)
            consumed = sum(lines.mapped("unit_amount"))
            contract.consumed_hours = consumed
            contract.remaining_hours = contract.included_hours - consumed
            contract.overrun_hours = max(consumed - contract.included_hours, 0.0)
            contract.active_ticket_count = len(contract.ticket_ids.filtered(lambda ticket: not ticket.closed))
            contract.covered_ticket_count = len(contract.ticket_ids)
            contract.utilization_rate = (
                round((consumed / contract.included_hours) * 100, 2)
                if contract.included_hours
                else 0.0
            )

    def _matches_ticket(self, ticket):
        self.ensure_one()
        ticket_partner = ticket.commercial_partner_id or ticket.partner_id.commercial_partner_id or ticket.partner_id
        if not ticket_partner or ticket_partner != self.partner_id:
            return False
        if self.team_id and ticket.team_id and self.team_id != ticket.team_id:
            return False
        ticket_date = fields.Date.to_date(ticket.create_date) if ticket.create_date else fields.Date.today()
        if self.start_date and ticket_date < self.start_date:
            return False
        if self.end_date and ticket_date > self.end_date:
            return False
        return True

    def action_activate(self):
        self.write({"manual_state": "active"})
        return True

    def action_suspend(self):
        self.write({"manual_state": "suspended"})
        return True

    def action_set_draft(self):
        self.write({"manual_state": "draft"})
        return True

    def action_cancel(self):
        self.write({"manual_state": "cancelled"})
        return True

    def action_open_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_mgmt.helpdesk_ticket_action"
        )
        action["domain"] = [("support_contract_id", "=", self.id)]
        action["context"] = {"search_default_open": 0}
        return action

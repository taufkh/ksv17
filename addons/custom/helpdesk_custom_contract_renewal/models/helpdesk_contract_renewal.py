from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskContractRenewal(models.Model):
    _name = "helpdesk.contract.renewal"
    _description = "Helpdesk Contract Renewal"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_follow_up_date asc, end_date asc, id desc"

    state_selection = [
        ("open", "Open"),
        ("in_review", "In Review"),
        ("handoff_sent", "Handoff Sent"),
        ("won", "Won"),
        ("lost", "Lost"),
        ("dismissed", "Dismissed"),
    ]
    trigger_selection = [
        ("expiry", "Contract Expiry"),
        ("low_hours", "Low Remaining Hours"),
        ("both", "Expiry And Low Hours"),
        ("manual", "Manual Review"),
    ]
    risk_selection = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    name = fields.Char(required=True, tracking=True)
    contract_id = fields.Many2one(
        "helpdesk.support.contract",
        string="Support Contract",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    partner_id = fields.Many2one(
        related="contract_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="contract_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        readonly=True,
    )
    team_id = fields.Many2one(
        related="contract_id.team_id",
        store=True,
        readonly=True,
        string="Helpdesk Team",
    )
    contract_type = fields.Selection(
        related="contract_id.contract_type",
        store=True,
        readonly=True,
    )
    contract_state = fields.Selection(
        related="contract_id.state",
        store=True,
        readonly=True,
        string="Contract State",
    )
    end_date = fields.Date(
        related="contract_id.end_date",
        store=True,
        readonly=True,
    )
    included_hours = fields.Float(
        related="contract_id.included_hours",
        readonly=True,
    )
    remaining_hours = fields.Float(
        related="contract_id.remaining_hours",
        readonly=True,
    )
    warning_hours = fields.Float(
        related="contract_id.warning_hours",
        readonly=True,
    )
    latest_ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Latest Support Ticket",
        compute="_compute_latest_ticket_id",
        compute_sudo=True,
    )
    trigger_type = fields.Selection(
        selection=trigger_selection,
        required=True,
        default="manual",
        tracking=True,
    )
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="open",
        tracking=True,
    )
    risk_level = fields.Selection(
        selection=risk_selection,
        compute="_compute_contract_signals",
        store=True,
    )
    days_to_expiry = fields.Integer(
        compute="_compute_contract_signals",
        store=True,
    )
    low_hours_alert = fields.Boolean(
        compute="_compute_contract_signals",
        store=True,
    )
    threshold_reached = fields.Boolean(
        compute="_compute_contract_signals",
        store=True,
    )
    is_auto_generated = fields.Boolean(default=False, tracking=True)
    owner_id = fields.Many2one(
        "res.users",
        string="Renewal Owner",
        default=lambda self: self.env.user,
        tracking=True,
    )
    sales_team_id = fields.Many2one(
        "crm.team",
        string="Sales Team",
        tracking=True,
    )
    sales_user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        tracking=True,
    )
    renewal_probability = fields.Integer(
        string="Renewal Probability (%)",
        default=50,
        tracking=True,
    )
    expected_revenue = fields.Monetary(tracking=True)
    next_follow_up_date = fields.Date(tracking=True)
    commercial_note = fields.Html(string="Commercial Note")
    decision_note = fields.Text(tracking=True)
    handoff_id = fields.Many2one(
        "helpdesk.sales.handoff",
        string="Sales Handoff",
        readonly=True,
        copy=False,
        tracking=True,
    )

    @api.depends("contract_id.ticket_ids", "contract_id.ticket_ids.write_date")
    def _compute_latest_ticket_id(self):
        for renewal in self:
            renewal.latest_ticket_id = renewal.contract_id._get_latest_support_ticket()

    @api.depends(
        "contract_id.end_date",
        "contract_id.remaining_hours",
        "contract_id.warning_hours",
        "contract_id.included_hours",
        "contract_id.state",
        "trigger_type",
    )
    def _compute_contract_signals(self):
        today = fields.Date.today()
        for renewal in self:
            days_to_expiry = 9999
            if renewal.end_date:
                days_to_expiry = (renewal.end_date - today).days
            low_hours_alert = bool(
                renewal.included_hours
                and renewal.contract_state in {"active", "expiring"}
                and renewal.remaining_hours <= renewal.warning_hours
            )
            threshold_reached = (
                renewal.trigger_type == "manual"
                or low_hours_alert
                or days_to_expiry <= 14
            )
            if days_to_expiry < 0 or (renewal.included_hours and renewal.remaining_hours < 0):
                risk_level = "critical"
            elif low_hours_alert or days_to_expiry <= 3:
                risk_level = "high"
            elif days_to_expiry <= 7:
                risk_level = "medium"
            else:
                risk_level = "low"
            renewal.days_to_expiry = days_to_expiry if days_to_expiry != 9999 else 0
            renewal.low_hours_alert = low_hours_alert
            renewal.threshold_reached = threshold_reached
            renewal.risk_level = risk_level

    @api.model
    def _get_trigger_type(self, contract):
        today = fields.Date.today()
        days_to_expiry = 9999
        if contract.end_date:
            days_to_expiry = (contract.end_date - today).days
        expiry = contract.state in {"active", "expiring"} and days_to_expiry <= 14
        low_hours = bool(
            contract.included_hours
            and contract.state in {"active", "expiring"}
            and contract.remaining_hours <= contract.warning_hours
        )
        if expiry and low_hours:
            return "both"
        if expiry:
            return "expiry"
        if low_hours:
            return "low_hours"
        return "manual"

    @api.model
    def _contract_requires_watch(self, contract):
        return (
            contract.state in {"active", "expiring"}
            and self._get_trigger_type(contract) != "manual"
        )

    @api.model
    def _prepare_watch_vals(self, contract, auto_generated=True):
        trigger_type = self._get_trigger_type(contract)
        probability = 70 if trigger_type in {"expiry", "both"} else 55
        return {
            "name": _("%(contract)s - Renewal Watch") % {"contract": contract.name},
            "contract_id": contract.id,
            "trigger_type": trigger_type,
            "state": "open",
            "owner_id": self.env.user.id,
            "next_follow_up_date": contract.end_date or fields.Date.today(),
            "renewal_probability": probability,
            "expected_revenue": 0.0,
            "is_auto_generated": auto_generated,
            "commercial_note": _(
                "<p>Auto-generated renewal review because the contract is nearing expiry "
                "or the remaining support balance is below the warning threshold.</p>"
            ),
        }

    @api.model
    def cron_sync_contract_renewals(self):
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.renewal.watch"):
            return True
        contract_model = self.env["helpdesk.support.contract"].sudo()
        renewal_model = self.sudo()
        contracts = contract_model.search([("state", "in", ["active", "expiring"])])
        for contract in contracts:
            if not renewal_model._contract_requires_watch(contract):
                continue
            existing = renewal_model.search(
                [
                    ("contract_id", "=", contract.id),
                    ("state", "in", ["open", "in_review", "handoff_sent"]),
                ],
                limit=1,
            )
            vals = renewal_model._prepare_watch_vals(contract)
            if existing:
                existing.write(
                    {
                        "trigger_type": vals["trigger_type"],
                        "next_follow_up_date": vals["next_follow_up_date"],
                        "is_auto_generated": True,
                    }
                )
            else:
                renewal = renewal_model.create(vals)
                renewal.message_post(
                    body=_(
                        "Renewal watch created automatically because this contract needs commercial follow-up."
                    )
                )
        return True

    def action_mark_in_review(self):
        self.write({"state": "in_review"})
        return True

    def action_mark_won(self):
        self.write({"state": "won"})
        return True

    def action_mark_lost(self):
        self.write({"state": "lost"})
        return True

    def action_dismiss(self):
        self.write({"state": "dismissed"})
        return True

    def action_reset_open(self):
        self.write({"state": "open"})
        return True

    def action_create_sales_handoff(self):
        self.ensure_one()
        if self.handoff_id:
            return self.action_open_handoff()
        ticket = self.latest_ticket_id or self.contract_id._get_latest_support_ticket()
        if not ticket:
            raise UserError(
                _(
                    "A renewal sales handoff needs at least one support ticket linked to the contract."
                )
            )
        handoff = self.env["helpdesk.sales.handoff"].create(
            {
                "name": _("%(contract)s - Renewal Follow-up")
                % {"contract": self.contract_id.name},
                "ticket_id": ticket.id,
                "source_contract_id": self.contract_id.id,
                "reason": "renewal",
                "urgency": "urgent" if self.risk_level == "critical" else "high",
                "sales_team_id": self.sales_team_id.id,
                "sales_user_id": self.sales_user_id.id,
                "expected_revenue": self.expected_revenue,
                "note": self.commercial_note
                or _(
                    "<p>Renewal watch escalated from support contract monitoring.</p>"
                ),
            }
        )
        self.write({"handoff_id": handoff.id, "state": "handoff_sent"})
        self.message_post(
            body=_("Sales handoff %(name)s created for renewal follow-up.")
            % {"name": handoff.display_name}
        )
        return handoff.get_formview_action()

    def action_open_contract(self):
        self.ensure_one()
        return self.contract_id.get_formview_action()

    def action_open_handoff(self):
        self.ensure_one()
        if not self.handoff_id:
            return False
        return self.handoff_id.get_formview_action()

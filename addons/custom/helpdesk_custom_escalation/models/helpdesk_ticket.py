from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    escalated = fields.Boolean(copy=False, tracking=True, index=True)
    priority_change_date = fields.Datetime(copy=False, tracking=True)
    last_escalation_rule_id = fields.Many2one(
        "helpdesk.escalation.rule",
        string="Last Escalation Rule",
        copy=False,
        readonly=True,
    )
    last_escalation_at = fields.Datetime(copy=False, readonly=True)
    next_escalation_rule_id = fields.Many2one(
        "helpdesk.escalation.rule",
        compute="_compute_next_escalation_info",
        string="Next Escalation Rule",
    )
    next_escalation_at = fields.Datetime(
        compute="_compute_next_escalation_info",
        string="Next Escalation At",
    )
    escalation_event_ids = fields.One2many(
        "helpdesk.escalation.event",
        "ticket_id",
        string="Escalation Events",
    )
    escalation_event_count = fields.Integer(compute="_compute_escalation_event_count")

    @api.depends("escalation_event_ids")
    def _compute_escalation_event_count(self):
        data = self.env["helpdesk.escalation.event"].read_group(
            [("ticket_id", "in", self.ids)],
            ["ticket_id"],
            ["ticket_id"],
        )
        counts = {item["ticket_id"][0]: item["ticket_id_count"] for item in data}
        for ticket in self:
            ticket.escalation_event_count = counts.get(ticket.id, 0)

    @api.depends(
        "team_id",
        "stage_id",
        "sla_deadline",
        "sla_expired",
        "priority_change_date",
        "escalation_event_ids",
    )
    def _compute_next_escalation_info(self):
        rule_model = self.env["helpdesk.escalation.rule"]
        for ticket in self:
            ticket.next_escalation_rule_id = False
            ticket.next_escalation_at = False
            if ticket.closed or not ticket.team_id:
                continue
            rules = rule_model.search(
                [("active", "=", True), ("team_id", "=", ticket.team_id.id)],
                order="sequence, id",
            )
            next_rule = False
            next_at = False
            for rule in rules:
                if rule._has_fired_for_ticket(ticket):
                    continue
                candidate = rule._get_next_trigger_at(ticket)
                if candidate and (not next_at or candidate < next_at):
                    next_at = candidate
                    next_rule = rule
            ticket.next_escalation_rule_id = next_rule
            ticket.next_escalation_at = next_at

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            if "priority_change_date" not in vals:
                vals["priority_change_date"] = now
        return super().create(vals_list)

    def write(self, vals):
        if "priority" in vals:
            vals["priority_change_date"] = fields.Datetime.now()
        return super().write(vals)

    def action_view_escalation_events(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "helpdesk_custom_escalation.action_helpdesk_escalation_event"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {"default_ticket_id": self.id}
        return action

    def _message_is_internal(self, message):
        self.ensure_one()
        if not message.author_id:
            return False
        return bool(message.author_id.user_ids.filtered(lambda user: not user.share))

    def _get_pending_customer_reply_datetime(self):
        self.ensure_one()
        messages = self.env["mail.message"].sudo().search(
            [
                ("model", "=", "helpdesk.ticket"),
                ("res_id", "=", self.id),
                ("message_type", "in", ["comment", "email"]),
                ("author_id", "!=", False),
            ],
            order="date desc, id desc",
        )
        latest_customer_message = False
        latest_internal_message = False
        for message in messages:
            if self._message_is_internal(message):
                if not latest_internal_message:
                    latest_internal_message = message
            elif not latest_customer_message:
                latest_customer_message = message
            if latest_customer_message and latest_internal_message:
                break
        if not latest_customer_message:
            return False
        if latest_internal_message and latest_internal_message.date > latest_customer_message.date:
            return False
        return latest_customer_message.date

    def _get_due_escalation_rules(self, now=None):
        self.ensure_one()
        now = fields.Datetime.to_datetime(now or fields.Datetime.now())
        rules = self.env["helpdesk.escalation.rule"].search(
            [("active", "=", True), ("team_id", "=", self.team_id.id)],
            order="sequence, id",
        )
        return rules.filtered(lambda rule: rule._is_due_for_ticket(self, now=now))

    @api.model
    def _cron_process_escalation_rules(self, batch_size=200):
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.ops.escalation"):
            return
        active_teams = self.env["helpdesk.escalation.rule"].search(
            [("active", "=", True)]
        ).mapped("team_id")
        if not active_teams:
            return
        tickets = self.search(
            [
                ("closed", "=", False),
                ("team_id", "in", active_teams.ids),
            ],
            order="priority desc, create_date asc",
            limit=batch_size,
        )
        now = fields.Datetime.now()
        for ticket in tickets:
            iterations = 0
            while iterations < 20:
                due_rules = ticket._get_due_escalation_rules(now=now)
                if not due_rules:
                    break
                due_rules[0].execute_for_ticket(ticket)
                iterations += 1

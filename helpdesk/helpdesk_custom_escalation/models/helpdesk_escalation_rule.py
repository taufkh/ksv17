from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HelpdeskEscalationRule(models.Model):
    _name = "helpdesk.escalation.rule"
    _description = "Helpdesk Escalation Rule"
    _order = "team_id, sequence, id"

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        "res.company",
        related="team_id.company_id",
        store=True,
        readonly=True,
    )
    team_user_ids = fields.Many2many(
        "res.users",
        related="team_id.user_ids",
        readonly=True,
    )
    parent_rule_id = fields.Many2one(
        "helpdesk.escalation.rule",
        string="After Rule",
        domain="[('team_id', '=', team_id), ('id', '!=', id)]",
    )
    child_rule_ids = fields.One2many(
        "helpdesk.escalation.rule",
        "parent_rule_id",
        string="Chained Rules",
    )
    trigger = fields.Selection(
        [
            ("sla_breach", "SLA Breach"),
            ("no_reply", "No Reply"),
            ("priority_change", "Priority Change"),
            ("age", "Ticket Age"),
        ],
        required=True,
        default="sla_breach",
        help=(
            "Root rules use this trigger to define their first deadline. "
            "Chained rules inherit timing from the parent rule execution."
        ),
    )
    threshold_hours = fields.Float(
        required=True,
        default=0.0,
        help="Hours to wait after the trigger or parent escalation.",
    )
    action = fields.Selection(
        [
            ("reassign", "Reassign"),
            ("notify", "Notify"),
            ("change_priority", "Change Priority"),
            ("change_stage", "Change Stage"),
        ],
        required=True,
        default="notify",
    )
    target_user_id = fields.Many2one(
        "res.users",
        string="Target User",
        domain="[('share', '=', False), ('id', 'in', team_user_ids)]",
    )
    notify_user_ids = fields.Many2many(
        "res.users",
        "helpdesk_escalation_rule_notify_user_rel",
        "rule_id",
        "user_id",
        string="Notify Users",
        domain="[('share', '=', False)]",
    )
    new_priority = fields.Selection(
        selection=[
            ("0", "Low"),
            ("1", "Medium"),
            ("2", "High"),
            ("3", "Very High"),
        ],
        string="New Priority",
    )
    stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Target Stage",
        domain="['|', ('team_ids', '=', False), ('team_ids', '=', team_id)]",
    )
    note = fields.Text()
    event_count = fields.Integer(compute="_compute_event_count")

    def _compute_event_count(self):
        event_data = self.env["helpdesk.escalation.event"].read_group(
            [("rule_id", "in", self.ids)],
            ["rule_id"],
            ["rule_id"],
        )
        counts = {data["rule_id"][0]: data["rule_id_count"] for data in event_data}
        for rule in self:
            rule.event_count = counts.get(rule.id, 0)

    def action_view_events(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "helpdesk_custom_escalation.action_helpdesk_escalation_event"
        )
        action["domain"] = [("rule_id", "=", self.id)]
        action["context"] = {"default_rule_id": self.id}
        return action

    def _get_parent_event(self, ticket):
        self.ensure_one()
        if not self.parent_rule_id:
            return self.env["helpdesk.escalation.event"]
        return self.env["helpdesk.escalation.event"].search(
            [
                ("ticket_id", "=", ticket.id),
                ("rule_id", "=", self.parent_rule_id.id),
            ],
            limit=1,
        )

    def _get_reference_datetime(self, ticket):
        self.ensure_one()
        if not ticket or ticket.team_id != self.team_id or ticket.closed:
            return False
        if self.parent_rule_id:
            parent_event = self._get_parent_event(ticket)
            return parent_event.event_date if parent_event else False
        if self.trigger == "age":
            return ticket.create_date
        if self.trigger == "priority_change":
            return ticket.priority_change_date or ticket.create_date
        if self.trigger == "sla_breach":
            if ticket.sla_deadline and ticket.sla_expired:
                return ticket.sla_deadline
            return False
        if self.trigger == "no_reply":
            return ticket._get_pending_customer_reply_datetime()
        return False

    def _get_next_trigger_at(self, ticket):
        self.ensure_one()
        reference_dt = self._get_reference_datetime(ticket)
        if not reference_dt:
            return False
        return fields.Datetime.to_datetime(reference_dt) + timedelta(
            hours=self.threshold_hours
        )

    def _has_fired_for_ticket(self, ticket):
        self.ensure_one()
        return bool(
            self.env["helpdesk.escalation.event"].search_count(
                [
                    ("ticket_id", "=", ticket.id),
                    ("rule_id", "=", self.id),
                ]
            )
        )

    def _is_due_for_ticket(self, ticket, now=None):
        self.ensure_one()
        now = fields.Datetime.to_datetime(now or fields.Datetime.now())
        if self._has_fired_for_ticket(ticket):
            return False
        next_trigger_at = self._get_next_trigger_at(ticket)
        return bool(next_trigger_at and next_trigger_at <= now)

    def _get_action_label(self):
        self.ensure_one()
        if self.action == "reassign":
            return _("reassigned to %s", self.target_user_id.name)
        if self.action == "notify":
            return _("notification sent")
        if self.action == "change_priority":
            priority_labels = dict(self._fields["new_priority"].selection)
            return _("priority changed to %s", priority_labels.get(self.new_priority))
        if self.action == "change_stage":
            return _("stage changed to %s", self.stage_id.name)
        return self.action

    def _get_notification_partner_ids(self):
        self.ensure_one()
        partners = self.notify_user_ids.mapped("partner_id")
        if self.action == "reassign" and self.target_user_id:
            partners |= self.target_user_id.partner_id
        return partners.ids

    def execute_for_ticket(self, ticket):
        self.ensure_one()
        if not self._is_due_for_ticket(ticket):
            return self.env["helpdesk.escalation.event"]

        values = {}
        if self.action == "reassign":
            values["user_id"] = self.target_user_id.id
        elif self.action == "change_priority":
            values["priority"] = self.new_priority
        elif self.action == "change_stage":
            values["stage_id"] = self.stage_id.id

        if values:
            ticket.write(values)

        reason = _(
            "Escalation rule '%(rule)s' fired for trigger '%(trigger)s' after %(hours)s hour(s).",
            rule=self.name,
            trigger=self.parent_rule_id and self.parent_rule_id.name or self.trigger,
            hours=self.threshold_hours,
        )
        event = self.env["helpdesk.escalation.event"].create(
            {
                "ticket_id": ticket.id,
                "rule_id": self.id,
                "reason": reason,
                "target_user_id": self.target_user_id.id,
                "notify_user_ids": [(6, 0, self.notify_user_ids.ids)],
            }
        )

        body = _(
            "<p><strong>Escalation executed</strong></p>"
            "<p>Rule: %(rule)s</p>"
            "<p>Action: %(action)s</p>"
            "<p>Reason: %(reason)s</p>",
            rule=self.name,
            action=self._get_action_label(),
            reason=reason,
        )
        if self.note:
            body += _("<p>Note: %s</p>", self.note)

        ticket.message_post(
            body=body,
            partner_ids=self._get_notification_partner_ids(),
            subtype_xmlid="mail.mt_note",
        )
        ticket.write(
            {
                "escalated": True,
                "last_escalation_rule_id": self.id,
                "last_escalation_at": event.event_date,
            }
        )
        return event

    @api.constrains(
        "threshold_hours",
        "parent_rule_id",
        "team_id",
        "action",
        "target_user_id",
        "stage_id",
        "new_priority",
    )
    def _check_action_requirements(self):
        for rule in self:
            if rule.threshold_hours < 0:
                raise ValidationError(_("Threshold hours must be zero or greater."))
            if rule.parent_rule_id and rule.parent_rule_id.team_id != rule.team_id:
                raise ValidationError(
                    _("Chained rules must belong to the same helpdesk team.")
                )
            if rule.action == "reassign" and not rule.target_user_id:
                raise ValidationError(_("Target user is required for reassign action."))
            if (
                rule.action == "reassign"
                and rule.target_user_id
                and rule.target_user_id not in rule.team_id.user_ids
            ):
                raise ValidationError(
                    _("Target user must belong to the selected helpdesk team.")
                )
            if rule.action == "change_stage" and not rule.stage_id:
                raise ValidationError(_("Target stage is required for stage changes."))
            if rule.action == "change_priority" and not rule.new_priority:
                raise ValidationError(
                    _("New priority is required for priority change action.")
                )

    @api.constrains("parent_rule_id")
    def _check_rule_recursion(self):
        for rule in self:
            current = rule.parent_rule_id
            visited = {rule.id}
            while current:
                if current.id in visited:
                    raise ValidationError(
                        _("Escalation rules cannot reference themselves.")
                    )
                visited.add(current.id)
                current = current.parent_rule_id

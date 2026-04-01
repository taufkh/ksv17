from odoo import fields, models


class HelpdeskEscalationEvent(models.Model):
    _name = "helpdesk.escalation.event"
    _description = "Helpdesk Escalation Event"
    _order = "event_date desc, id desc"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        required=True,
        ondelete="cascade",
        index=True,
    )
    rule_id = fields.Many2one(
        "helpdesk.escalation.rule",
        required=True,
        ondelete="cascade",
        index=True,
    )
    team_id = fields.Many2one(
        "helpdesk.ticket.team",
        related="ticket_id.team_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="ticket_id.company_id",
        store=True,
        readonly=True,
    )
    event_date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    action = fields.Selection(
        related="rule_id.action",
        store=True,
        readonly=True,
    )
    reason = fields.Text(required=True)
    target_user_id = fields.Many2one("res.users", string="Assigned To")
    notify_user_ids = fields.Many2many(
        "res.users",
        "helpdesk_escalation_event_notify_user_rel",
        "event_id",
        "user_id",
        string="Notified Users",
    )
    executed_by_id = fields.Many2one(
        "res.users",
        string="Executed By",
        default=lambda self: self.env.user,
        readonly=True,
    )

    _sql_constraints = [
        (
            "helpdesk_escalation_event_ticket_rule_unique",
            "unique(ticket_id, rule_id)",
            "Each escalation rule can only be executed once per ticket.",
        )
    ]

    def name_get(self):
        result = []
        for event in self:
            name = f"{event.ticket_id.number} - {event.rule_id.name}"
            result.append((event.id, name))
        return result

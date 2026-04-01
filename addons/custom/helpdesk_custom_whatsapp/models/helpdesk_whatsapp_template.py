from collections import defaultdict

from odoo import _, fields, models


class SafeDict(defaultdict):
    def __missing__(self, key):
        return ""


class HelpdeskWhatsappTemplate(models.Model):
    _name = "helpdesk.whatsapp.template"
    _description = "Helpdesk WhatsApp Template"
    _order = "sequence, id"

    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    team_id = fields.Many2one("helpdesk.ticket.team", string="Team")
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    trigger = fields.Selection(
        [
            ("stage_update", "Stage Update"),
            ("ticket_closed", "Ticket Closed"),
            ("escalation", "Escalation"),
            ("manual", "Manual"),
        ],
        required=True,
        default="stage_update",
    )
    recipient_type = fields.Selection(
        [
            ("customer", "Customer"),
            ("assignee", "Assigned User"),
            ("team_lead", "Team Lead"),
            ("escalation_watchers", "Escalation Watchers"),
        ],
        required=True,
        default="customer",
    )
    body_template = fields.Text(
        required=True,
        help=(
            "Use placeholders like {ticket_number}, {ticket_name}, {stage_name}, "
            "{partner_name}, {team_name}, {sla_label}, {public_portal_url}, "
            "{rule_name}, {event_reason}, {changed_by_name}."
        ),
    )

    def _get_candidate_templates(self, ticket, trigger):
        return self.search(
            [
                ("active", "=", True),
                ("trigger", "=", trigger),
                ("company_id", "in", [False, ticket.company_id.id]),
                "|",
                ("team_id", "=", False),
                ("team_id", "=", ticket.team_id.id),
            ],
            order="sequence, id",
        )

    def _get_recipient_partners(self, ticket, event=False):
        self.ensure_one()
        partners = self.env["res.partner"]
        if self.recipient_type == "customer" and ticket.partner_id:
            if ticket.partner_id.mobile or ticket.partner_id.phone:
                partners |= ticket.partner_id
            elif ticket.partner_id.commercial_partner_id:
                partners |= ticket.partner_id.commercial_partner_id
        elif self.recipient_type == "assignee" and ticket.user_id.partner_id:
            partners |= ticket.user_id.partner_id
        elif self.recipient_type == "team_lead" and ticket.team_id.user_id.partner_id:
            partners |= ticket.team_id.user_id.partner_id
        elif self.recipient_type == "escalation_watchers" and event:
            partners |= event.notify_user_ids.mapped("partner_id")
            if event.target_user_id.partner_id:
                partners |= event.target_user_id.partner_id
        return partners

    def _prepare_render_context(self, ticket, event=False, recipient=False, extra_context=None):
        self.ensure_one()
        ticket._ensure_public_portal_token(regenerate=False)
        priority_labels = dict(ticket._fields["priority"].selection)
        context = {
            "ticket_number": ticket.number or "",
            "ticket_name": ticket.name or "",
            "team_name": ticket.team_id.name or "",
            "stage_name": ticket.stage_id.name or "",
            "partner_name": ticket.partner_id.name or "",
            "assignee_name": ticket.user_id.name or "",
            "priority_name": priority_labels.get(ticket.priority, ""),
            "sla_deadline": fields.Datetime.to_string(ticket.sla_deadline)
            if ticket.sla_deadline
            else "",
            "sla_label": getattr(ticket, "public_portal_sla_label", "") or "",
            "public_portal_url": ticket.public_portal_url or "",
            "recipient_name": recipient.name if recipient else "",
            "rule_name": event.rule_id.name if event else "",
            "event_reason": event.reason if event else "",
            "changed_by_name": self.env.user.name,
            "closed_date": fields.Datetime.to_string(ticket.closed_date)
            if ticket.closed_date
            else "",
        }
        if extra_context:
            context.update(extra_context)
        return SafeDict(str, context)

    def _render_message_body(self, ticket, event=False, recipient=False, extra_context=None):
        self.ensure_one()
        return (self.body_template or "").format_map(
            self._prepare_render_context(ticket, event=event, recipient=recipient, extra_context=extra_context)
        ).strip()

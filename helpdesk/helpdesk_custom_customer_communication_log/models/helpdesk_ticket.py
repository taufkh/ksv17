import re

from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    communication_log_ids = fields.One2many(
        "helpdesk.communication.log",
        "ticket_id",
        string="Communication Logs",
    )
    communication_log_count = fields.Integer(
        compute="_compute_communication_summary",
        store=True,
    )
    last_communication_at = fields.Datetime(
        compute="_compute_communication_summary",
        store=True,
    )
    last_communication_channel = fields.Selection(
        selection=[
            ("portal", "Portal"),
            ("whatsapp", "WhatsApp"),
            ("email", "Email"),
            ("phone", "Phone"),
            ("api", "API"),
            ("manual", "Manual"),
        ],
        compute="_compute_communication_summary",
        store=True,
    )

    @api.depends("communication_log_ids", "communication_log_ids.logged_at", "communication_log_ids.channel")
    def _compute_communication_summary(self):
        for ticket in self:
            logs = ticket.communication_log_ids.sorted(
                key=lambda log: log.logged_at or fields.Datetime.now(),
                reverse=True,
            )
            ticket.communication_log_count = len(logs)
            ticket.last_communication_at = logs[:1].logged_at if logs else False
            ticket.last_communication_channel = logs[:1].channel if logs else False

    def _communication_plaintext(self, text):
        if not text:
            return False
        clean = re.sub(r"<[^>]+>", " ", text)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:1000] if clean else False

    def _create_communication_log(
        self,
        *,
        channel,
        direction,
        communication_type,
        status="done",
        subject=False,
        summary=False,
        body=False,
        partner=False,
        user=False,
        source_model=False,
        source_res_id=False,
        logged_at=False,
        release_note=False,
    ):
        self.ensure_one()
        subject = subject or _("%(channel)s communication") % {
            "channel": dict(
                self.env["helpdesk.communication.log"]._fields["channel"].selection
            ).get(channel, channel)
        }
        values = {
            "ticket_id": self.id,
            "partner_id": partner.id if partner else (self.partner_id.id or False),
            "user_id": user.id if user else self.env.user.id,
            "channel": channel,
            "direction": direction,
            "communication_type": communication_type,
            "status": status,
            "subject": subject,
            "summary": summary or self._communication_plaintext(body),
            "body": self._communication_plaintext(body),
            "logged_at": logged_at or fields.Datetime.now(),
            "source_model": source_model,
            "source_res_id": source_res_id,
            "release_note_id": release_note.id if release_note else False,
        }
        return self.env["helpdesk.communication.log"].create(values)

    def action_open_communication_logs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_customer_communication_log.action_helpdesk_communication_log"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {"default_ticket_id": self.id}
        return action

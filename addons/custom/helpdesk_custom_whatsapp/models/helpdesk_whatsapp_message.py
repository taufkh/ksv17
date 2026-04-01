import json
import logging
import re
from datetime import timedelta

import requests

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class HelpdeskWhatsappMessage(models.Model):
    _name = "helpdesk.whatsapp.message"
    _description = "Helpdesk WhatsApp Message"
    _order = "create_date desc, id desc"

    name = fields.Char(compute="_compute_name", store=True)
    active = fields.Boolean(default=True)
    ticket_id = fields.Many2one("helpdesk.ticket", required=True, ondelete="cascade")
    template_id = fields.Many2one("helpdesk.whatsapp.template", ondelete="set null")
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
    trigger = fields.Selection(
        [
            ("stage_update", "Stage Update"),
            ("ticket_closed", "Ticket Closed"),
            ("escalation", "Escalation"),
            ("manual", "Manual"),
        ],
        required=True,
    )
    recipient_partner_id = fields.Many2one("res.partner", string="Recipient")
    recipient_name = fields.Char(required=True)
    recipient_phone = fields.Char(required=True)
    body = fields.Text(required=True)
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        default="queued",
        required=True,
        index=True,
    )
    scheduled_at = fields.Datetime(default=fields.Datetime.now, required=True)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True)
    sent_at = fields.Datetime()
    attempt_count = fields.Integer(default=0)
    max_attempts = fields.Integer(default=3, required=True)
    is_sandbox = fields.Boolean(default=False)
    provider_message_id = fields.Char()
    provider_response = fields.Text()
    error_message = fields.Text()
    source_model = fields.Char()
    source_res_id = fields.Integer()

    @api.depends("ticket_id", "recipient_name", "trigger")
    def _compute_name(self):
        labels = dict(self._fields["trigger"].selection)
        for message in self:
            message.name = "%s - %s - %s" % (
                message.ticket_id.number or _("Ticket"),
                labels.get(message.trigger, message.trigger),
                message.recipient_name or _("Recipient"),
            )

    @api.model
    def _get_default_country_code(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.default_country_code", default="+62")
        )

    @api.model
    def _get_retry_interval_minutes(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.retry_interval_minutes", default="15")
        )
        try:
            return max(int(value or 15), 1)
        except (TypeError, ValueError):
            return 15

    @api.model
    def _get_max_attempts(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.max_attempts", default="3")
        )
        try:
            return max(int(value or 3), 1)
        except (TypeError, ValueError):
            return 3

    @api.model
    def _is_enabled(self):
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.channel.whatsapp"):
            return False
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.enabled", default="True")
        )
        return str(value).lower() not in {"0", "false", "no"}

    @api.model
    def _is_sandbox_mode(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.sandbox_mode", default="True")
        )
        return str(value).lower() not in {"0", "false", "no"}

    @api.model
    def _get_api_url(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "helpdesk_custom_whatsapp.api_url",
                default="https://graph.facebook.com/v20.0",
            )
            .rstrip("/")
        )

    @api.model
    def _get_phone_number_id(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.phone_number_id", default="")
            .strip()
        )

    @api.model
    def _get_access_token(self):
        return (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_whatsapp.access_token", default="")
            .strip()
        )

    @api.model
    def _normalize_phone(self, phone):
        if not phone:
            return False
        phone = phone.strip()
        if not phone:
            return False
        digits = re.sub(r"\D", "", phone)
        if not digits:
            return False
        country = self._get_default_country_code()
        country_digits = re.sub(r"\D", "", country or "")
        if phone.startswith("+"):
            return "+%s" % digits
        if digits.startswith("00"):
            return "+%s" % digits[2:]
        if digits.startswith("0") and country_digits:
            return "+%s%s" % (country_digits, digits[1:])
        if country_digits and digits.startswith(country_digits):
            return "+%s" % digits
        if country_digits:
            return "+%s%s" % (country_digits, digits)
        return "+%s" % digits

    @api.model
    def _prepare_queue_values(
        self,
        ticket,
        template,
        recipient_partner,
        phone,
        body,
        trigger,
        source_record=False,
    ):
        return {
            "ticket_id": ticket.id,
            "template_id": template.id if template else False,
            "trigger": trigger,
            "recipient_partner_id": recipient_partner.id if recipient_partner else False,
            "recipient_name": recipient_partner.name if recipient_partner else _("Unknown"),
            "recipient_phone": phone,
            "body": body,
            "state": "queued",
            "scheduled_at": fields.Datetime.now(),
            "next_attempt_at": fields.Datetime.now(),
            "max_attempts": self._get_max_attempts(),
            "source_model": source_record._name if source_record else False,
            "source_res_id": source_record.id if source_record else False,
        }

    def _get_meta_cloud_payload(self):
        self.ensure_one()
        return {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": self.recipient_phone.replace("+", ""),
            "type": "text",
            "text": {
                "preview_url": True,
                "body": self.body[:4096],
            },
        }

    def _send_via_meta_cloud(self):
        self.ensure_one()
        endpoint = "%s/%s/messages" % (self._get_api_url(), self._get_phone_number_id())
        headers = {
            "Authorization": "Bearer %s" % self._get_access_token(),
            "Content-Type": "application/json",
        }
        response = requests.post(
            endpoint,
            headers=headers,
            json=self._get_meta_cloud_payload(),
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    def _mark_sent(self, response_payload, *, sandbox=False):
        self.ensure_one()
        provider_message_id = False
        if isinstance(response_payload, dict):
            provider_message_id = (
                response_payload.get("messages", [{}])[0].get("id")
                or response_payload.get("message_id")
            )
        self.write(
            {
                "state": "sent",
                "sent_at": fields.Datetime.now(),
                "provider_message_id": provider_message_id,
                "provider_response": json.dumps(response_payload, indent=2, sort_keys=True)
                if isinstance(response_payload, (dict, list))
                else str(response_payload),
                "error_message": False,
                "is_sandbox": sandbox,
            }
        )
        ticket = self.ticket_id
        if ticket and "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="whatsapp",
                direction="outbound",
                communication_type="notification",
                status="sent",
                subject=self.name,
                summary=self.body,
                body=self.body,
                partner=self.recipient_partner_id or ticket.partner_id,
                user=self.env.user,
                source_model=self._name,
                source_res_id=self.id,
                logged_at=self.sent_at or fields.Datetime.now(),
            )

    def _mark_failure(self, error_message):
        self.ensure_one()
        next_attempt = fields.Datetime.now() + timedelta(
            minutes=self._get_retry_interval_minutes()
        )
        next_state = "queued"
        if self.attempt_count >= self.max_attempts:
            next_state = "failed"
            next_attempt = False
        self.write(
            {
                "state": next_state,
                "error_message": error_message,
                "next_attempt_at": next_attempt,
            }
        )
        ticket = self.ticket_id
        if next_state == "failed" and ticket and "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="whatsapp",
                direction="outbound",
                communication_type="notification",
                status="failed",
                subject=_("WhatsApp delivery failed"),
                summary=error_message,
                body=self.body,
                partner=self.recipient_partner_id or ticket.partner_id,
                user=self.env.user,
                source_model=self._name,
                source_res_id=self.id,
            )

    def _process_single_message(self):
        self.ensure_one()
        if self.state not in {"queued", "failed"}:
            return
        if not self._is_enabled():
            self.write(
                {
                    "state": "cancelled",
                    "error_message": _("WhatsApp notifications are disabled."),
                }
            )
            return

        self.write({"attempt_count": self.attempt_count + 1})
        if self._is_sandbox_mode():
            self._mark_sent(
                {
                    "sandbox": True,
                    "message": "Delivered in sandbox mode",
                    "to": self.recipient_phone,
                },
                sandbox=True,
            )
            return

        if not self._get_phone_number_id() or not self._get_access_token():
            self._mark_failure(_("Missing WhatsApp API credentials."))
            return

        try:
            payload = self._send_via_meta_cloud()
            self._mark_sent(payload, sandbox=False)
        except requests.exceptions.Timeout:
            self._mark_failure(_("WhatsApp API request timed out."))
        except requests.exceptions.HTTPError as exc:
            body = exc.response.text[:500] if exc.response is not None else str(exc)
            _logger.error("WhatsApp HTTP error for message %s: %s", self.id, body)
            self._mark_failure(_("WhatsApp API error: %s") % body)
        except requests.exceptions.ConnectionError:
            self._mark_failure(_("Could not connect to WhatsApp API."))
        except Exception as exc:  # pragma: no cover - final safety net
            _logger.exception("Unexpected WhatsApp send error for message %s", self.id)
            self._mark_failure(str(exc))

    @api.model
    def _cron_process_queue(self, limit=100):
        if not self._is_enabled():
            return
        messages = self.search(
            [
                ("state", "=", "queued"),
                ("next_attempt_at", "<=", fields.Datetime.now()),
            ],
            order="scheduled_at asc, id asc",
            limit=limit,
        )
        for message in messages:
            message._process_single_message()

    def action_retry(self):
        self.write(
            {
                "state": "queued",
                "next_attempt_at": fields.Datetime.now(),
                "error_message": False,
            }
        )

    def action_cancel(self):
        self.write({"state": "cancelled"})

    def action_process_now(self):
        for message in self:
            message.write({"state": "queued", "next_attempt_at": fields.Datetime.now()})
            message._process_single_message()

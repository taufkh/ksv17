import secrets
import re
import math
from urllib.parse import quote
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.tools import html2plaintext, html_escape, plaintext2html


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    CSAT_ACTIVITY_SUMMARY_FOLLOWUP = "Customer follow-up needed"
    CSAT_ACTIVITY_SUMMARY_LOW = "Low CSAT recovery required"
    CSAT_ACTIVITY_SUMMARY_RESOLUTION = "Complete resolution summary"

    PUBLIC_PORTAL_REOPEN_REASONS = [
        ("issue_not_resolved", "Issue Not Resolved"),
        ("issue_returned", "Issue Returned"),
        ("new_impact", "New Business Impact"),
        ("request_follow_up", "Need Further Follow-up"),
    ]
    PUBLIC_PORTAL_DIGEST_MODES = [
        ("instant", "Instant Updates"),
        ("daily", "Daily Digest"),
        ("weekly", "Weekly Digest"),
    ]
    PUBLIC_PORTAL_ESCALATION_CHANNELS = [
        ("email", "Email"),
        ("whatsapp", "WhatsApp"),
        ("phone", "Phone Call"),
    ]

    public_portal_token = fields.Char(copy=False, index=True)
    public_portal_token_valid_until = fields.Datetime(copy=False)
    public_portal_token_revoked = fields.Boolean(copy=False, default=False)
    public_portal_last_view_at = fields.Datetime(copy=False, readonly=True)
    public_portal_view_count = fields.Integer(copy=False, readonly=True)
    public_portal_url = fields.Char(
        string="Public Portal URL", compute="_compute_public_portal_url"
    )
    public_portal_state = fields.Selection(
        [
            ("missing", "Missing"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("revoked", "Revoked"),
        ],
        compute="_compute_public_portal_state",
    )
    public_portal_rating_token = fields.Char(
        string="Portal Rating Token", compute="_compute_public_portal_rating_token"
    )
    public_portal_has_pending_rating = fields.Boolean(
        string="Pending Portal Rating",
        compute="_compute_public_portal_has_pending_rating",
    )
    public_portal_can_reopen = fields.Boolean(
        string="Can Reopen from Portal", compute="_compute_public_portal_can_reopen"
    )
    public_portal_can_escalate = fields.Boolean(
        string="Can Escalate from Portal", compute="_compute_public_portal_can_escalate"
    )
    public_portal_sla_status = fields.Selection(
        [
            ("no_sla", "No SLA"),
            ("safe", "Within SLA"),
            ("risk", "Approaching SLA"),
            ("breached", "SLA Breached"),
            ("closed", "Closed"),
        ],
        string="Portal SLA Status",
        compute="_compute_public_portal_sla_status",
    )
    public_portal_sla_label = fields.Char(
        string="Portal SLA Label", compute="_compute_public_portal_sla_status"
    )
    public_portal_sla_remaining_hours = fields.Float(
        string="Portal SLA Remaining Hours",
        compute="_compute_public_portal_sla_status",
    )
    public_portal_notify_email = fields.Boolean(
        string="Portal Notify by Email",
        default=True,
        copy=False,
    )
    public_portal_notify_whatsapp = fields.Boolean(
        string="Portal Notify by WhatsApp",
        default=False,
        copy=False,
    )
    public_portal_digest_mode = fields.Selection(
        selection=PUBLIC_PORTAL_DIGEST_MODES,
        string="Portal Notification Frequency",
        default="instant",
        copy=False,
    )
    public_portal_last_digest_sent_at = fields.Datetime(
        string="Last Portal Digest Sent At",
        copy=False,
        readonly=True,
    )
    public_portal_last_digest_attempt_at = fields.Datetime(
        string="Last Portal Digest Attempt At",
        copy=False,
        readonly=True,
    )
    public_portal_digest_failure_count = fields.Integer(
        string="Portal Digest Failure Count",
        copy=False,
        readonly=True,
        default=0,
    )
    public_portal_last_digest_error = fields.Text(
        string="Last Portal Digest Error",
        copy=False,
        readonly=True,
    )
    public_portal_collaborator_ids = fields.Many2many(
        "res.partner",
        "helpdesk_ticket_public_collaborator_rel",
        "ticket_id",
        "partner_id",
        string="Portal Collaborators",
        copy=False,
    )
    public_portal_last_reopen_reason = fields.Selection(
        selection=PUBLIC_PORTAL_REOPEN_REASONS,
        string="Last Portal Reopen Reason",
        copy=False,
        readonly=True,
    )
    public_portal_last_reopen_detail = fields.Text(
        string="Last Portal Reopen Detail",
        copy=False,
        readonly=True,
    )
    public_portal_last_reopen_at = fields.Datetime(
        string="Last Portal Reopen At",
        copy=False,
        readonly=True,
    )
    public_portal_last_escalation_reason = fields.Text(
        string="Last Portal Escalation Reason",
        copy=False,
        readonly=True,
    )
    public_portal_last_escalation_channel = fields.Selection(
        selection=PUBLIC_PORTAL_ESCALATION_CHANNELS,
        string="Last Portal Escalation Preferred Channel",
        copy=False,
        readonly=True,
    )
    public_portal_last_escalation_callback_at = fields.Datetime(
        string="Last Portal Escalation Callback Requested At",
        copy=False,
        readonly=True,
    )
    public_portal_last_escalation_at = fields.Datetime(
        string="Last Portal Escalation At",
        copy=False,
        readonly=True,
    )
    public_portal_escalation_count = fields.Integer(
        string="Portal Escalation Request Count",
        copy=False,
        readonly=True,
        default=0,
    )
    public_portal_resolution_summary = fields.Text(
        string="Resolution Summary",
        copy=False,
        help="Customer-friendly summary of the final resolution.",
    )
    public_portal_last_customer_update_at = fields.Datetime(
        string="Last Customer Update At",
        copy=False,
        readonly=True,
    )
    public_portal_last_support_update_at = fields.Datetime(
        string="Last Support Update At",
        copy=False,
        readonly=True,
    )
    public_portal_last_followup_activity_at = fields.Datetime(
        string="Last Customer Follow-up Reminder At",
        copy=False,
        readonly=True,
    )
    public_portal_last_low_csat_at = fields.Datetime(
        string="Last Low CSAT At",
        copy=False,
        readonly=True,
    )
    public_portal_low_csat_count = fields.Integer(
        string="Low CSAT Count",
        copy=False,
        readonly=True,
        default=0,
    )

    @api.depends(
        "public_portal_token",
        "public_portal_token_valid_until",
        "public_portal_token_revoked",
    )
    def _compute_public_portal_url(self):
        base_url = (
            self.env["ir.config_parameter"].sudo().get_param("web.base.url", "").rstrip("/")
        )
        now = fields.Datetime.now()
        for ticket in self:
            if (
                not base_url
                or not ticket.public_portal_token
                or ticket.public_portal_token_revoked
                or (
                    ticket.public_portal_token_valid_until
                    and ticket.public_portal_token_valid_until < now
                )
            ):
                ticket.public_portal_url = False
            else:
                ticket.public_portal_url = (
                    f"{base_url}/helpdesk/track/{ticket.public_portal_token}"
                    f"?db={self.env.cr.dbname}"
                )

    @api.depends(
        "public_portal_token",
        "public_portal_token_valid_until",
        "public_portal_token_revoked",
    )
    def _compute_public_portal_state(self):
        now = fields.Datetime.now()
        for ticket in self:
            if not ticket.public_portal_token:
                ticket.public_portal_state = "missing"
            elif ticket.public_portal_token_revoked:
                ticket.public_portal_state = "revoked"
            elif (
                ticket.public_portal_token_valid_until
                and ticket.public_portal_token_valid_until < now
            ):
                ticket.public_portal_state = "expired"
            else:
                ticket.public_portal_state = "active"

    @api.depends("rating_ids.consumed", "stage_id.rating_mail_template_id", "closed_date")
    def _compute_public_portal_has_pending_rating(self):
        for ticket in self:
            ticket.public_portal_has_pending_rating = bool(
                ticket.stage_id.rating_mail_template_id
                and ticket.closed_date
                and not ticket.rating_ids.filtered("consumed")
            )

    @api.depends(
        "closed_date",
        "team_id.portal_allow_reopen",
        "team_id.portal_reopen_stage_id",
    )
    def _compute_public_portal_can_reopen(self):
        for ticket in self:
            ticket.public_portal_can_reopen = bool(
                ticket.closed_date
                and ticket.team_id.portal_allow_reopen
                and ticket._get_public_portal_reopen_stage()
            )

    @api.depends(
        "closed_date",
        "team_id.portal_allow_escalation",
        "team_id.portal_escalation_stage_id",
    )
    def _compute_public_portal_can_escalate(self):
        for ticket in self:
            ticket.public_portal_can_escalate = bool(
                not ticket.closed_date
                and ticket.team_id.portal_allow_escalation
            )

    @api.depends("closed_date", "sla_deadline")
    def _compute_public_portal_sla_status(self):
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.closed_date:
                ticket.public_portal_sla_status = "closed"
                ticket.public_portal_sla_label = _("Closed")
                ticket.public_portal_sla_remaining_hours = 0
            elif not ticket.sla_deadline:
                ticket.public_portal_sla_status = "no_sla"
                ticket.public_portal_sla_label = _("No SLA committed")
                ticket.public_portal_sla_remaining_hours = 0
            else:
                remaining_hours = (ticket.sla_deadline - now).total_seconds() / 3600.0
                ticket.public_portal_sla_remaining_hours = remaining_hours
                if remaining_hours < 0:
                    ticket.public_portal_sla_status = "breached"
                    ticket.public_portal_sla_label = _(
                        "Overdue by %.1f hours"
                    ) % abs(remaining_hours)
                elif remaining_hours <= 8:
                    ticket.public_portal_sla_status = "risk"
                    ticket.public_portal_sla_label = _(
                        "%.1f hours remaining"
                    ) % remaining_hours
                else:
                    ticket.public_portal_sla_status = "safe"
                    ticket.public_portal_sla_label = _(
                        "%.1f hours remaining"
                    ) % remaining_hours

    def _compute_public_portal_rating_token(self):
        for ticket in self:
            ticket.public_portal_rating_token = (
                ticket._rating_get_access_token() if ticket.id else False
            )

    @api.model
    def _get_public_portal_validity_days(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.public_token_validity_days", default="30")
        )
        try:
            return max(int(value or 30), 1)
        except (TypeError, ValueError):
            return 30

    @api.model
    def _get_public_portal_allowed_extensions(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param(
                "helpdesk_custom_portal.allowed_extensions",
                default="pdf,png,jpg,jpeg,txt,csv,xlsx,docx,zip",
            )
        )
        extensions = {extension.strip().lower() for extension in (value or "").split(",")}
        return {extension for extension in extensions if extension}

    @api.model
    def _get_public_portal_max_attachment_bytes(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.max_attachment_mb", default="10")
        )
        try:
            return int(float(value or 10) * 1024 * 1024)
        except (TypeError, ValueError):
            return 10 * 1024 * 1024

    @api.model
    def _is_public_portal_enabled(self):
        if not self.env["helpdesk.feature.config"].is_enabled("helpdesk.channel.portal"):
            return False
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.public_tracking_enabled", default="True")
        )
        return str(value).lower() not in {"0", "false", "no"}

    def _ensure_public_portal_token(self, regenerate=False):
        now = fields.Datetime.now()
        validity = now + timedelta(days=self._get_public_portal_validity_days())
        for ticket in self:
            values = {}
            if regenerate or not ticket.public_portal_token:
                values["public_portal_token"] = secrets.token_urlsafe(24)
            if regenerate or ticket.public_portal_token_revoked:
                values["public_portal_token_revoked"] = False
            if (
                regenerate
                or not ticket.public_portal_token_valid_until
                or ticket.public_portal_token_valid_until < now
            ):
                values["public_portal_token_valid_until"] = validity
            if values:
                ticket.write(values)
        return True

    def _register_public_portal_visit(self):
        self.ensure_one()
        self.sudo().write(
            {
                "public_portal_last_view_at": fields.Datetime.now(),
                "public_portal_view_count": self.public_portal_view_count + 1,
            }
        )

    @api.model
    def _get_ticket_by_public_portal_token(self, token):
        if not token or not self._is_public_portal_enabled():
            return self.browse()
        ticket = self.sudo().search(
            [
                ("public_portal_token", "=", token),
                ("public_portal_token_revoked", "=", False),
            ],
            limit=1,
        )
        if (
            not ticket
            or (
                ticket.public_portal_token_valid_until
                and ticket.public_portal_token_valid_until < fields.Datetime.now()
            )
        ):
            return self.browse()
        ticket._portal_ensure_token()
        return ticket

    def _validate_public_portal_attachment(self, filename, file_size):
        self.ensure_one()
        allowed_extensions = self._get_public_portal_allowed_extensions()
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if allowed_extensions and extension not in allowed_extensions:
            return _(
                "File type not allowed. Allowed extensions: %s"
            ) % ", ".join(sorted(allowed_extensions))
        if file_size > self._get_public_portal_max_attachment_bytes():
            max_mb = self._get_public_portal_max_attachment_bytes() / (1024 * 1024)
            return _("File is too large. Maximum allowed size is %.1f MB.") % max_mb
        return False

    def action_generate_public_portal_link(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=False)
        return self.action_open_public_portal_link()

    def action_regenerate_public_portal_link(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=True)
        self.message_post(
            body=_("Public tracking link has been refreshed."),
            subtype_xmlid="mail.mt_note",
        )
        return self.action_open_public_portal_link()

    def action_revoke_public_portal_link(self):
        self.ensure_one()
        self.write({"public_portal_token_revoked": True})
        self.message_post(
            body=_("Public tracking link has been revoked."),
            subtype_xmlid="mail.mt_note",
        )
        return True

    def action_open_public_portal_link(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=False)
        return {
            "type": "ir.actions.act_url",
            "url": self.public_portal_url,
            "target": "new",
        }

    def _get_public_portal_share_recipients(self):
        self.ensure_one()
        recipients = (
            self.partner_id | self.public_portal_collaborator_ids
        ).sudo().filtered(lambda partner: partner.email)
        if recipients:
            return recipients
        pool = self._get_public_portal_collaborator_pool()
        return pool.filtered(lambda partner: partner.email)[:5]

    def _get_public_portal_whatsapp_recipients(self):
        self.ensure_one()
        recipients = (self.partner_id | self.public_portal_collaborator_ids).sudo().filtered(
            lambda partner: partner.mobile or partner.phone
        )
        if recipients:
            return recipients
        pool = self._get_public_portal_collaborator_pool()
        return pool.filtered(lambda partner: partner.mobile or partner.phone)[:5]

    def _get_public_portal_share_template_values(self):
        self.ensure_one()
        return {
            "ticket_number": self.number or "-",
            "ticket_title": self.name or "-",
            "customer_name": self.partner_id.name or _("Customer"),
            "team_name": self.team_id.name or _("Support Team"),
            "portal_url": self.public_portal_url or "",
            "portal_expiry": (
                fields.Datetime.to_string(self.public_portal_token_valid_until)
                if self.public_portal_token_valid_until
                else _("Not set")
            ),
        }

    def _render_public_portal_share_template(self, template_text):
        self.ensure_one()
        values = self._get_public_portal_share_template_values()
        rendered = template_text or ""
        for key, value in values.items():
            rendered = rendered.replace("{%s}" % key, value or "")
        return rendered

    def _get_public_portal_share_email_subject(self):
        self.ensure_one()
        template = (
            self.team_id.portal_share_email_subject_template
            if "portal_share_email_subject_template" in self.team_id._fields
            else False
        )
        template = template or "[{ticket_number}] Public Ticket Tracking Link"
        return self._render_public_portal_share_template(template)

    def _get_public_portal_share_email_body(self):
        self.ensure_one()
        template = (
            self.team_id.portal_share_email_template
            if "portal_share_email_template" in self.team_id._fields
            else False
        )
        template = template or (
            "Hello {customer_name},\n\n"
            "You can track ticket {ticket_number} - {ticket_title} using the secure public link:\n"
            "{portal_url}\n\n"
            "Link validity: {portal_expiry}\n\n"
            "Regards,\n"
            "{team_name}"
        )
        return self._render_public_portal_share_template(template)

    def _get_public_portal_share_whatsapp_body(self):
        self.ensure_one()
        template = (
            self.team_id.portal_share_whatsapp_template
            if "portal_share_whatsapp_template" in self.team_id._fields
            else False
        )
        template = template or (
            "Hello {customer_name}, this is your support ticket link.\n"
            "Ticket: {ticket_number} - {ticket_title}\n"
            "Track here: {portal_url}\n"
            "Valid until: {portal_expiry}"
        )
        return self._render_public_portal_share_template(template)

    def action_copy_public_portal_link(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=False)
        if not self.public_portal_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "Public portal link is not available. Please refresh the link first."
                    ),
                },
            }
        recipients = self._get_public_portal_share_recipients()
        whatsapp_recipients = self._get_public_portal_whatsapp_recipients()
        wizard_form = self.env.ref(
            "helpdesk_custom_portal.view_helpdesk_public_portal_share_wizard_form"
        )
        return {
            "name": _("Copy Public Portal Link"),
            "type": "ir.actions.act_window",
            "res_model": "helpdesk.public.portal.share.wizard",
            "view_mode": "form",
            "views": [(wizard_form.id, "form")],
            "view_id": wizard_form.id,
            "target": "new",
            "context": {
                "default_ticket_id": self.id,
                "default_public_portal_url": self.public_portal_url,
                "default_email_subject_preview": self._get_public_portal_share_email_subject(),
                "default_email_body_preview": self._get_public_portal_share_email_body(),
                "default_whatsapp_body_preview": self._get_public_portal_share_whatsapp_body(),
                "default_recipient_emails": ", ".join(recipients.mapped("email")),
                "default_recipient_phones": ", ".join(
                    sorted(
                        set(
                            phone
                            for phone in whatsapp_recipients.mapped("mobile")
                            + whatsapp_recipients.mapped("phone")
                            if phone
                        )
                    )
                ),
            },
        }

    def action_send_public_portal_link_email(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=False)
        if not self.public_portal_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "Public portal link is not available. Please refresh the link first."
                    ),
                },
            }

        recipients = self._get_public_portal_share_recipients()
        if not recipients:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "No customer contact email found. Please set customer email or add portal collaborators."
                    ),
                },
            }

        subject = self._get_public_portal_share_email_subject()
        body_text = self._get_public_portal_share_email_body()
        body_html = plaintext2html(body_text)
        mail = self.env["mail.mail"].sudo().create(
            {
                "subject": subject,
                "body_html": body_html,
                "email_to": ",".join(recipients.mapped("email")),
                "auto_delete": False,
                "model": self._name,
                "res_id": self.id,
            }
        )
        send_error = False
        try:
            mail.send()
            mail.flush_recordset()
            mail.invalidate_recordset()
            if mail.state == "exception":
                send_error = mail.failure_reason or _("Mail delivery exception.")
        except Exception as exc:  # pragma: no cover - safety for runtime failures
            send_error = str(exc)

        recipient_names = ", ".join(recipients.mapped("name"))
        if send_error:
            self.message_post(
                body=_("Public portal link email failed: %s") % send_error,
                subtype_xmlid="mail.mt_note",
            )
            if "communication_log_ids" in self._fields:
                self._create_communication_log(
                    channel="email",
                    direction="outbound",
                    communication_type="notification",
                    status="failed",
                    subject=_("Public portal link email failed"),
                    summary=send_error,
                    body=body_text,
                    partner=self.partner_id,
                    source_model=mail._name,
                    source_res_id=mail.id,
                )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "Public portal link email failed. Check outgoing email configuration."
                    ),
                },
            }

        self.message_post(
            body=_("Public portal link emailed to: %s") % recipient_names,
            subtype_xmlid="mail.mt_note",
        )
        if "communication_log_ids" in self._fields:
            self._create_communication_log(
                channel="email",
                direction="outbound",
                communication_type="notification",
                status="sent",
                subject=_("Public portal link emailed"),
                summary=_("Shared with %s contact(s).") % len(recipients),
                body=body_text,
                partner=self.partner_id,
                source_model=mail._name,
                source_res_id=mail.id,
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "sticky": False,
                "message": _("Public portal link email has been sent."),
            },
        }

    def action_send_public_portal_link_whatsapp(self):
        self.ensure_one()
        self._ensure_public_portal_token(regenerate=False)
        if not self.public_portal_url:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "Public portal link is not available. Please refresh the link first."
                    ),
                },
            }

        whatsapp_body = self._get_public_portal_share_whatsapp_body()
        recipients = self._get_public_portal_whatsapp_recipients()
        if not recipients:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": False,
                    "message": _(
                        "No customer phone number found. Please set mobile/phone on customer or collaborators."
                    ),
                },
            }

        if "helpdesk.whatsapp.message" in self.env:
            queue_model = self.env["helpdesk.whatsapp.message"].sudo()
            recipient = self.env["res.partner"]
            normalized_phone = False
            for candidate in recipients:
                normalized_phone = queue_model._normalize_phone(
                    candidate.mobile or candidate.phone
                )
                if normalized_phone:
                    recipient = candidate
                    break
            if not normalized_phone:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "type": "warning",
                        "sticky": False,
                        "message": _(
                            "Phone format is invalid for WhatsApp delivery. Update customer phone number first."
                        ),
                    },
                }

            message = queue_model.create(
                {
                    "ticket_id": self.id,
                    "trigger": "manual",
                    "recipient_partner_id": recipient.id,
                    "recipient_name": recipient.name or _("Customer"),
                    "recipient_phone": normalized_phone,
                    "body": whatsapp_body,
                    "state": "queued",
                    "scheduled_at": fields.Datetime.now(),
                    "next_attempt_at": fields.Datetime.now(),
                    "max_attempts": queue_model._get_max_attempts(),
                }
            )
            self.message_post(
                body=_(
                    "Public portal link queued for WhatsApp delivery to %s (%s)."
                )
                % (recipient.name, normalized_phone),
                subtype_xmlid="mail.mt_note",
            )
            if "communication_log_ids" in self._fields:
                self._create_communication_log(
                    channel="whatsapp",
                    direction="outbound",
                    communication_type="notification",
                    status="done",
                    subject=_("Public portal link queued for WhatsApp"),
                    summary=_("Queued for %s") % (recipient.name or _("Customer")),
                    body=whatsapp_body,
                    partner=recipient,
                    source_model=message._name,
                    source_res_id=message.id,
                )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "sticky": False,
                    "message": _(
                        "Public portal link has been queued for WhatsApp delivery."
                    ),
                },
            }

        raw_phone = recipients[:1].mobile or recipients[:1].phone
        phone_digits = re.sub(r"\D", "", raw_phone or "")
        whatsapp_url = (
            "https://wa.me/%s?text=%s" % (phone_digits, quote(whatsapp_body))
            if phone_digits
            else "https://wa.me/?text=%s" % quote(whatsapp_body)
        )
        self.message_post(
            body=_("Public portal link prepared for WhatsApp share."),
            subtype_xmlid="mail.mt_note",
        )
        if "communication_log_ids" in self._fields:
            self._create_communication_log(
                channel="whatsapp",
                direction="outbound",
                communication_type="notification",
                status="done",
                subject=_("Public portal link shared via WhatsApp URL"),
                summary=_("Opened WhatsApp sharing URL."),
                body=whatsapp_body,
                partner=recipients[:1],
                source_model=self._name,
                source_res_id=self.id,
            )
        return {"type": "ir.actions.act_url", "url": whatsapp_url, "target": "new"}

    def action_share_public_portal_link(self):
        return self.action_send_public_portal_link_email()

    def _get_public_portal_csat_recovery_user(self):
        self.ensure_one()
        return self.team_id.user_id or self.user_id or self.env.user

    def _touch_public_portal_customer_update(self, when_dt=False):
        self.ensure_one()
        self.sudo().write(
            {"public_portal_last_customer_update_at": when_dt or fields.Datetime.now()}
        )

    def _touch_public_portal_support_update(self, when_dt=False):
        self.ensure_one()
        self.sudo().write(
            {"public_portal_last_support_update_at": when_dt or fields.Datetime.now()}
        )

    def _is_public_portal_customer_followup_due(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.closed or not self.public_portal_last_customer_update_at:
            return False
        if (
            self.public_portal_last_support_update_at
            and self.public_portal_last_support_update_at
            >= self.public_portal_last_customer_update_at
        ):
            return False
        due_at = self.public_portal_last_customer_update_at + timedelta(
            hours=self._get_public_portal_customer_followup_reminder_hours()
        )
        if due_at > now:
            return False
        if (
            self.public_portal_last_followup_activity_at
            and self.public_portal_last_followup_activity_at
            >= self.public_portal_last_customer_update_at
        ):
            return False
        return True

    def _schedule_public_portal_customer_followup_activity(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if not self._is_public_portal_customer_followup_due(now=now):
            return False
        target_user = self._get_public_portal_csat_recovery_user()
        if not target_user:
            return False
        summary = self.CSAT_ACTIVITY_SUMMARY_FOLLOWUP
        activity = self.env["mail.activity"].sudo().search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("user_id", "=", target_user.id),
                ("summary", "=", summary),
            ],
            limit=1,
        )
        if not activity:
            note = _(
                "Customer has not received a support update after the latest portal/customer interaction."
            )
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=target_user.id,
                date_deadline=fields.Date.to_date(now),
                summary=summary,
                note=note,
            )
        self.write({"public_portal_last_followup_activity_at": now})
        if "communication_log_ids" in self._fields:
            self._create_communication_log(
                channel="manual",
                direction="outbound",
                communication_type="follow_up",
                status="done",
                subject=_("CSAT follow-up reminder scheduled"),
                summary=_("Follow-up activity scheduled for %s.")
                % (target_user.name or _("Support owner")),
                body=_(
                    "Reason: no support response since %s."
                )
                % fields.Datetime.to_string(self.public_portal_last_customer_update_at),
                partner=self.partner_id,
                source_model=self._name,
                source_res_id=self.id,
            )
        return True

    def _trigger_public_portal_low_csat_recovery(self, rate_value, feedback=False):
        self.ensure_one()
        threshold = self._get_public_portal_low_csat_threshold()
        if rate_value > threshold:
            return False
        now = fields.Datetime.now()
        self.write(
            {
                "public_portal_last_low_csat_at": now,
                "public_portal_low_csat_count": self.public_portal_low_csat_count + 1,
            }
        )
        target_user = self._get_public_portal_csat_recovery_user()
        summary = self.CSAT_ACTIVITY_SUMMARY_LOW
        note_lines = [
            _("Customer submitted low CSAT score: %s/5") % rate_value,
        ]
        if feedback:
            note_lines.append(_("Customer feedback:\n%s") % feedback)
        if target_user:
            activity = self.env["mail.activity"].sudo().search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("user_id", "=", target_user.id),
                    ("summary", "=", summary),
                ],
                limit=1,
            )
            if not activity:
                due_hours = self._get_public_portal_low_csat_recovery_due_hours()
                due_dt = now + timedelta(hours=due_hours)
                self.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=target_user.id,
                    date_deadline=fields.Date.to_date(due_dt),
                    summary=summary,
                    note="\n\n".join(note_lines),
                )
        self.with_context(skip_public_portal_touch=True).message_post(
            body=plaintext2html("\n".join(note_lines)),
            subtype_xmlid="mail.mt_note",
        )
        if "communication_log_ids" in self._fields:
            self._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="feedback",
                status="done",
                subject=_("Low CSAT recovery initiated"),
                summary=_("Low CSAT %s/5 received.") % rate_value,
                body="\n".join(note_lines),
                partner=self.partner_id,
                source_model=self._name,
                source_res_id=self.id,
            )
        return True

    def message_post(self, **kwargs):
        result = super().message_post(**kwargs)
        if len(self) != 1 or self.env.context.get("skip_public_portal_touch"):
            return result
        ticket = self
        if not result or result._name != "mail.message":
            return result
        author = result.author_id
        when_dt = result.date or fields.Datetime.now()
        if not author:
            return result
        internal_user = author.user_ids.filtered(lambda user: not user.share)
        if internal_user:
            ticket._touch_public_portal_support_update(when_dt=when_dt)
            return result
        customer_root = (
            ticket.partner_id.commercial_partner_id if ticket.partner_id else False
        )
        if customer_root and author.commercial_partner_id == customer_root:
            ticket._touch_public_portal_customer_update(when_dt=when_dt)
        return result

    def write(self, vals):
        result = super().write(vals)
        if "stage_id" in vals:
            for ticket in self:
                if ticket.closed and not ticket.public_portal_resolution_summary:
                    ticket.public_portal_resolution_summary = _(
                        "Resolution summary is pending and will be updated by support."
                    )
                    owner = ticket._get_public_portal_csat_recovery_user()
                    if owner:
                        existing = self.env["mail.activity"].sudo().search(
                            [
                                ("res_model", "=", ticket._name),
                                ("res_id", "=", ticket.id),
                                ("user_id", "=", owner.id),
                                ("summary", "=", ticket.CSAT_ACTIVITY_SUMMARY_RESOLUTION),
                            ],
                            limit=1,
                        )
                        if not existing:
                            ticket.activity_schedule(
                                "mail.mail_activity_data_todo",
                                user_id=owner.id,
                                date_deadline=fields.Date.today(),
                                summary=ticket.CSAT_ACTIVITY_SUMMARY_RESOLUTION,
                                note=_(
                                    "Ticket was closed without a clear customer-facing resolution summary. "
                                    "Please complete the summary to improve CSAT clarity."
                                ),
                            )
                if ticket.closed and ticket.public_portal_resolution_summary:
                    ticket._touch_public_portal_support_update()
        return result

    def rating_apply(
        self,
        rate,
        token=None,
        rating=None,
        feedback=None,
        subtype_xmlid=None,
        notify_delay_send=False,
    ):
        result = super().rating_apply(
            rate,
            token=token,
            rating=rating,
            feedback=feedback,
            subtype_xmlid=subtype_xmlid,
            notify_delay_send=notify_delay_send,
        )
        try:
            rate_value = int(rate or 0)
        except (TypeError, ValueError):
            rate_value = 0
        for ticket in self:
            ticket._trigger_public_portal_low_csat_recovery(
                rate_value=rate_value, feedback=feedback
            )
        return result

    def _is_public_portal_token_active(self):
        self.ensure_one()
        if not self.public_portal_token or self.public_portal_token_revoked:
            return False
        if (
            self.public_portal_token_valid_until
            and self.public_portal_token_valid_until < fields.Datetime.now()
        ):
            return False
        return True

    def _get_public_portal_digest_interval_days(self):
        self.ensure_one()
        mode = self._get_public_portal_effective_digest_mode()
        if mode == "daily":
            return 1
        if mode == "weekly":
            return 7
        return 0

    def _is_public_portal_digest_due(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self._get_public_portal_effective_digest_mode() == "disabled":
            return False
        if (
            not self.public_portal_notify_email
            or not self._is_public_portal_token_active()
        ):
            return False
        interval_days = self._get_public_portal_digest_interval_days()
        if not interval_days:
            return False
        if not self.public_portal_last_digest_sent_at:
            return True
        next_due = self.public_portal_last_digest_sent_at + timedelta(days=interval_days)
        return next_due <= now

    def _get_public_portal_digest_updates(self, since_dt=False, limit=8):
        self.ensure_one()
        messages = self.message_ids.sudo().filtered(
            lambda message: (
                message.date
                and message.message_type in ("comment", "email", "notification")
                and (message.body or message.attachment_ids or message.tracking_value_ids)
            )
        )
        if since_dt:
            messages = messages.filtered(lambda message: message.date >= since_dt)
        updates = []
        for message in messages.sorted("date", reverse=True)[:limit]:
            body_text = html2plaintext(message.body or "").strip()
            if not body_text and message.attachment_ids:
                body_text = _("Shared %s attachment(s).") % len(message.attachment_ids)
            if not body_text and message.tracking_value_ids:
                body_text = _("Ticket fields were updated.")
            body_text = " ".join(body_text.split())
            updates.append(
                {
                    "author": message.author_id.name or _("System"),
                    "date": message.date,
                    "summary": body_text or _("Update without text body."),
                }
            )
        return updates

    def _build_public_portal_digest_body(self, updates, digest_label):
        self.ensure_one()
        update_items = "".join(
            "<li><strong>%s</strong> (%s): %s</li>"
            % (
                html_escape(update["author"]),
                fields.Datetime.to_string(update["date"]),
                html_escape(update["summary"]),
            )
            for update in updates
        )
        return _(
            "<p>Hello,</p>"
            "<p>Here is your %(digest_label)s update for ticket <strong>%(ticket_number)s</strong> - %(ticket_name)s.</p>"
            "<p><strong>Current Stage:</strong> %(stage)s<br/>"
            "<strong>SLA:</strong> %(sla)s</p>"
            "<p><strong>Latest Updates:</strong></p>"
            "<ul>%(items)s</ul>"
            "<p>Track full details and collaborate via portal:</p>"
            "<p><a href=\"%(url)s\">%(url)s</a></p>"
            "<p>Regards,<br/>Support Team</p>"
        ) % {
            "digest_label": html_escape(digest_label),
            "ticket_number": html_escape(self.number or "-"),
            "ticket_name": html_escape(self.name or "-"),
            "stage": html_escape(self.stage_id.name or "-"),
            "sla": html_escape(self.public_portal_sla_label or _("No SLA committed")),
            "items": update_items or "<li>%s</li>" % html_escape(_("No new updates.")),
            "url": html_escape(self.public_portal_url or ""),
        }

    def _send_public_portal_digest(self, force=False, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        effective_mode = self._get_public_portal_effective_digest_mode()
        if effective_mode == "disabled":
            return False
        if not force and not self._is_public_portal_digest_due(now=now):
            return False
        if not self._is_public_portal_token_active():
            return False
        self.write({"public_portal_last_digest_attempt_at": now})
        recipients = self._get_public_portal_share_recipients().filtered(
            lambda partner: partner.email
        )
        if not recipients:
            return False
        interval_days = self._get_public_portal_digest_interval_days()
        since_dt = (
            self.public_portal_last_digest_sent_at
            or (now - timedelta(days=interval_days))
            if interval_days
            else False
        )
        updates = self._get_public_portal_digest_updates(since_dt=since_dt, limit=8)
        if not updates and not force:
            return False

        digest_map = self._get_public_portal_digest_map()
        digest_label = digest_map.get(effective_mode, _("Digest"))
        subject = _("%(number)s - %(digest)s Support Digest") % {
            "number": self.number or _("Ticket"),
            "digest": digest_label,
        }
        body_html = self._build_public_portal_digest_body(updates, digest_label)
        mail = self.env["mail.mail"].sudo().create(
            {
                "subject": subject,
                "body_html": body_html,
                "email_to": ",".join(recipients.mapped("email")),
                "auto_delete": False,
                "model": self._name,
                "res_id": self.id,
            }
        )
        send_error = False
        try:
            mail.send()
            mail.flush_recordset()
            mail.invalidate_recordset()
            if mail.state == "exception":
                send_error = mail.failure_reason or _("Mail delivery exception.")
        except Exception as exc:  # pragma: no cover - safety for runtime failures
            send_error = str(exc)

        if send_error:
            failure_count = self.public_portal_digest_failure_count + 1
            self.write(
                {
                    "public_portal_digest_failure_count": failure_count,
                    "public_portal_last_digest_error": send_error[:2000],
                }
            )
            if "communication_log_ids" in self._fields:
                self._create_communication_log(
                    channel="email",
                    direction="outbound",
                    communication_type="notification",
                    status="failed",
                    subject=_("Portal digest failed"),
                    summary=_("Digest delivery failed."),
                    body=_("Error: %s") % send_error,
                    partner=self.partner_id,
                    source_model=mail._name,
                    source_res_id=mail.id,
                )
            return False

        self.write(
            {
                "public_portal_last_digest_sent_at": now,
                "public_portal_digest_failure_count": 0,
                "public_portal_last_digest_error": False,
            }
        )
        if "communication_log_ids" in self._fields:
            self._create_communication_log(
                channel="email",
                direction="outbound",
                communication_type="notification",
                status="sent",
                subject=_("Portal digest sent"),
                summary=_("%s digest sent to %s recipients.")
                % (digest_label, len(recipients)),
                body=_("Recipients: %s\nPortal URL: %s")
                % (
                    ", ".join(recipients.mapped("email")),
                    self.public_portal_url or "-",
                ),
                partner=self.partner_id,
                source_model=mail._name,
                source_res_id=mail.id,
            )
        return True

    def action_send_public_portal_digest_now(self):
        self.ensure_one()
        sent = self._send_public_portal_digest(force=True)
        if sent:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "sticky": False,
                    "message": _("Portal digest has been sent to customer recipients."),
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "sticky": False,
                "message": _(
                    "Digest was not sent. Check recipient emails, link status, or recent ticket updates."
                ),
            },
        }

    @api.model
    def _cron_send_public_portal_digests(self, limit=200):
        if not self._is_public_portal_enabled():
            return 0
        now = fields.Datetime.now()
        tickets = self.search(
            [
                ("public_portal_notify_email", "=", True),
                ("public_portal_digest_mode", "in", ["daily", "weekly"]),
                ("public_portal_digest_failure_count", "=", 0),
                ("public_portal_token", "!=", False),
                ("public_portal_token_revoked", "=", False),
                "|",
                ("public_portal_token_valid_until", "=", False),
                ("public_portal_token_valid_until", ">=", now),
            ],
            order="public_portal_last_digest_sent_at asc, id asc",
            limit=limit,
        )
        sent_count = 0
        for ticket in tickets:
            if ticket._send_public_portal_digest(force=False, now=now):
                sent_count += 1
        return sent_count

    def _is_public_portal_digest_retry_due(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.public_portal_digest_failure_count <= 0:
            return False
        if not self.public_portal_last_digest_attempt_at:
            return True
        retry_minutes = self._get_public_portal_digest_retry_minutes()
        return self.public_portal_last_digest_attempt_at + timedelta(
            minutes=retry_minutes
        ) <= now

    def action_retry_public_portal_digest(self):
        self.ensure_one()
        sent = self._send_public_portal_digest(force=True)
        if sent:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "success",
                    "sticky": False,
                    "message": _("Portal digest retry succeeded."),
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning",
                "sticky": False,
                "message": _(
                    "Portal digest retry did not succeed. Please review digest error details."
                ),
            },
        }

    @api.model
    def _cron_retry_failed_public_portal_digests(self, limit=100):
        if not self._is_public_portal_enabled():
            return 0
        now = fields.Datetime.now()
        max_failures = self._get_public_portal_digest_max_failures()
        tickets = self.search(
            [
                ("public_portal_digest_failure_count", ">", 0),
                ("public_portal_digest_failure_count", "<=", max_failures),
                ("public_portal_notify_email", "=", True),
                ("public_portal_token", "!=", False),
                ("public_portal_token_revoked", "=", False),
                "|",
                ("public_portal_token_valid_until", "=", False),
                ("public_portal_token_valid_until", ">=", now),
            ],
            order="public_portal_last_digest_attempt_at asc, id asc",
            limit=limit,
        )
        retried = 0
        for ticket in tickets:
            if ticket._is_public_portal_digest_retry_due(now=now):
                ticket._send_public_portal_digest(force=True, now=now)
                retried += 1
        return retried

    @api.model
    def _cron_schedule_public_portal_customer_followups(self, limit=200):
        if not self._is_public_portal_enabled():
            return 0
        now = fields.Datetime.now()
        tickets = self.search(
            [
                ("closed", "=", False),
                ("partner_id", "!=", False),
                ("public_portal_last_customer_update_at", "!=", False),
            ],
            order="public_portal_last_customer_update_at asc, id asc",
            limit=limit,
        )
        scheduled = 0
        for ticket in tickets:
            if ticket._schedule_public_portal_customer_followup_activity(now=now):
                scheduled += 1
        return scheduled

    def _get_public_portal_timeline(self):
        self.ensure_one()
        timeline = []
        if self.create_date:
            timeline.append(
                {
                    "date": self.create_date,
                    "title": _("Ticket submitted"),
                    "detail": self.name,
                    "kind": "create",
                }
            )
        if self.assigned_date and self.user_id:
            timeline.append(
                {
                    "date": self.assigned_date,
                    "title": _("Assigned to %s") % self.user_id.name,
                    "detail": self.team_id.name or "",
                    "kind": "assign",
                }
            )
        for message in self.message_ids.sudo().sorted("date"):
            for tracking_value in message.tracking_value_ids.filtered(
                lambda value: value.field_id.name in {"stage_id", "user_id", "escalated"}
            ):
                old_label = tracking_value.old_value_char or ""
                new_label = tracking_value.new_value_char or ""
                if tracking_value.field_id.name == "stage_id":
                    title = _("Stage updated")
                    detail = _("%s -> %s") % (old_label or "-", new_label or "-")
                    kind = "stage"
                elif tracking_value.field_id.name == "user_id":
                    title = _("Assignment updated")
                    detail = _("%s -> %s") % (old_label or "-", new_label or "-")
                    kind = "assign"
                else:
                    title = _("Escalation status changed")
                    detail = _("%s -> %s") % (old_label or _("No"), new_label or _("Yes"))
                    kind = "escalation"
                timeline.append(
                    {
                        "date": message.date,
                        "title": title,
                        "detail": detail,
                        "kind": kind,
                    }
                )
        for event in self.escalation_event_ids.sorted("create_date"):
            timeline.append(
                {
                    "date": event.create_date,
                    "title": _("Escalated by rule"),
                    "detail": event.rule_id.name,
                    "kind": "escalation",
                }
            )
        for rating in self.rating_ids.filtered("consumed"):
            timeline.append(
                {
                    "date": rating.write_date or rating.create_date,
                    "title": _("Customer rating submitted"),
                    "detail": _("Score: %s / 5") % rating.rating,
                    "kind": "rating",
                }
            )
        if self.closed_date:
            timeline.append(
                {
                    "date": self.closed_date,
                    "title": _("Ticket closed"),
                    "detail": self.stage_id.name,
                    "kind": "close",
                }
            )
        return sorted(timeline, key=lambda item: item["date"] or fields.Datetime.now(), reverse=True)

    def _get_public_portal_reopen_stage(self):
        self.ensure_one()
        return (
            self.team_id.portal_reopen_stage_id
            or self.team_id._get_applicable_stages().filtered(lambda stage: not stage.closed)[:1]
        )

    def _get_public_portal_escalation_stage(self):
        self.ensure_one()
        return (
            self.team_id.portal_escalation_stage_id
            or self.team_id._get_applicable_stages().filtered(lambda stage: not stage.closed)[:1]
        )

    @api.model
    def _get_public_portal_reopen_reason_selection(self):
        return list(self.PUBLIC_PORTAL_REOPEN_REASONS)

    @api.model
    def _get_public_portal_reopen_reason_map(self):
        return dict(self.PUBLIC_PORTAL_REOPEN_REASONS)

    @api.model
    def _get_public_portal_escalation_channel_selection(self):
        return list(self.PUBLIC_PORTAL_ESCALATION_CHANNELS)

    @api.model
    def _get_public_portal_escalation_channel_map(self):
        return dict(self.PUBLIC_PORTAL_ESCALATION_CHANNELS)

    @api.model
    def _get_public_portal_escalation_cooldown_minutes(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.escalation_cooldown_minutes", default="120")
        )
        try:
            return max(int(value or 120), 5)
        except (TypeError, ValueError):
            return 120

    def _is_public_portal_escalation_allowed(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if not self.public_portal_last_escalation_at:
            return True, 0
        cooldown_minutes = self._get_public_portal_escalation_cooldown_minutes()
        next_allowed_at = self.public_portal_last_escalation_at + timedelta(
            minutes=cooldown_minutes
        )
        if now >= next_allowed_at:
            return True, 0
        remaining_seconds = max((next_allowed_at - now).total_seconds(), 0)
        remaining_minutes = int(math.ceil(remaining_seconds / 60.0))
        return False, remaining_minutes

    @api.model
    def _get_public_portal_low_csat_threshold(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.csat_low_score_threshold", default="3")
        )
        try:
            return min(max(int(value or 3), 1), 5)
        except (TypeError, ValueError):
            return 3

    @api.model
    def _get_public_portal_low_csat_recovery_due_hours(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.csat_recovery_due_hours", default="4")
        )
        try:
            return max(int(value or 4), 1)
        except (TypeError, ValueError):
            return 4

    @api.model
    def _get_public_portal_customer_followup_reminder_hours(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.customer_followup_reminder_hours", default="24")
        )
        try:
            return max(int(value or 24), 1)
        except (TypeError, ValueError):
            return 24

    @api.model
    def _get_public_portal_digest_selection(self):
        return list(self.PUBLIC_PORTAL_DIGEST_MODES)

    @api.model
    def _get_public_portal_digest_map(self):
        return dict(self.PUBLIC_PORTAL_DIGEST_MODES)

    @api.model
    def _get_public_portal_digest_retry_minutes(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.digest_retry_minutes", default="60")
        )
        try:
            return max(int(value or 60), 5)
        except (TypeError, ValueError):
            return 60

    @api.model
    def _get_public_portal_digest_max_failures(self):
        value = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("helpdesk_custom_portal.digest_max_failures", default="5")
        )
        try:
            return max(int(value or 5), 1)
        except (TypeError, ValueError):
            return 5

    def _get_public_portal_digest_policy(self):
        self.ensure_one()
        policy = (
            self.team_id.portal_digest_policy
            if "portal_digest_policy" in self.team_id._fields
            else "ticket"
        )
        return policy or "ticket"

    def _get_public_portal_effective_digest_mode(self):
        self.ensure_one()
        policy = self._get_public_portal_digest_policy()
        if policy == "disabled":
            return "disabled"
        if policy in {"daily", "weekly"}:
            return policy
        return self.public_portal_digest_mode or "instant"

    def _is_public_portal_digest_policy_locked(self):
        self.ensure_one()
        return self._get_public_portal_digest_policy() != "ticket"

    def _get_public_portal_collaborator_pool(self):
        self.ensure_one()
        root = self.partner_id.commercial_partner_id or self.partner_id
        if not root:
            return self.env["res.partner"]
        return (
            self.env["res.partner"]
            .sudo()
            .search(
                [
                    ("email", "!=", False),
                    ("commercial_partner_id", "=", root.id),
                ]
            )
        )

    def _get_public_portal_collaborators(self):
        self.ensure_one()
        collaborators = (self.partner_id | self.public_portal_collaborator_ids).sudo()
        return collaborators.sorted(key=lambda partner: (partner.name or "").lower())

    @api.model
    def _parse_public_portal_collaborator_emails(self, raw_emails):
        if not raw_emails:
            return []
        parts = re.split(r"[,\n;]+", raw_emails)
        normalized = []
        for part in parts:
            email = (part or "").strip().lower()
            if email and "@" in email and email not in normalized:
                normalized.append(email)
        return normalized

    def _update_public_portal_collaborators(self, raw_emails):
        self.ensure_one()
        emails = self._parse_public_portal_collaborator_emails(raw_emails)
        if not emails:
            return {
                "added_partners": self.env["res.partner"],
                "existing_partners": self.public_portal_collaborator_ids,
                "missing_emails": [],
            }
        pool = self._get_public_portal_collaborator_pool()
        email_map = {}
        for partner in pool:
            if partner.email:
                email_map[partner.email.strip().lower()] = partner
        added_partners = self.env["res.partner"]
        missing_emails = []
        for email in emails:
            partner = email_map.get(email)
            if partner:
                added_partners |= partner
            else:
                missing_emails.append(email)
        new_partners = added_partners - self.public_portal_collaborator_ids
        if new_partners:
            self.message_subscribe(partner_ids=new_partners.ids)
            self.write(
                {
                    "public_portal_collaborator_ids": [
                        (4, partner.id) for partner in new_partners
                    ]
                }
            )
        return {
            "added_partners": new_partners,
            "existing_partners": self.public_portal_collaborator_ids,
            "missing_emails": missing_emails,
        }

    def _remove_public_portal_collaborator(self, partner):
        self.ensure_one()
        if not partner or partner not in self.public_portal_collaborator_ids:
            return False
        self.write({"public_portal_collaborator_ids": [(3, partner.id)]})
        if partner in self.message_partner_ids:
            self.message_unsubscribe(partner_ids=[partner.id])
        return True

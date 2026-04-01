import base64

import werkzeug

from odoo import _, fields, http
from odoo.http import request
from odoo.tools import html2plaintext, plaintext2html

from odoo.addons.helpdesk_mgmt.controllers.myaccount import CustomerPortalHelpdesk


class HelpdeskCustomPortal(CustomerPortalHelpdesk):
    LOW_RATING_MAX = 3
    PUBLIC_REPLY_IMPACT_OPTIONS = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    PUBLIC_REPLY_URGENCY_OPTIONS = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
    ]

    def _is_portal_feature_enabled(self):
        return request.env["helpdesk.feature.config"].sudo().is_enabled(
            "helpdesk.channel.portal"
        )

    def _get_ticket_from_public_token(self, token):
        if not self._is_portal_feature_enabled():
            return request.env["helpdesk.ticket"]
        return request.env["helpdesk.ticket"].sudo()._get_ticket_by_public_portal_token(
            token
        )

    def _public_reply_impact_map(self):
        return dict(self.PUBLIC_REPLY_IMPACT_OPTIONS)

    def _public_reply_urgency_map(self):
        return dict(self.PUBLIC_REPLY_URGENCY_OPTIONS)

    def _is_truthy(self, value):
        return str(value or "").strip().lower() in {"1", "true", "on", "yes"}

    def _get_public_ticket_attachments(self, ticket):
        attachments = ticket.attachment_ids | ticket.message_ids.attachment_ids
        attachments = attachments.sudo()
        attachments.generate_access_token()
        return attachments

    def _get_public_ticket_messages(self, ticket):
        return (
            ticket.message_ids.sudo()
            .filtered(
                lambda message: (
                    message.body
                    or message.attachment_ids
                    or message.tracking_value_ids
                )
                and message.message_type in ("comment", "email", "notification")
            )
            .sorted("date", reverse=True)
        )

    def _get_public_collaborator_activity(self, ticket, limit=10):
        collaborators = ticket._get_public_portal_collaborators()
        if not collaborators:
            return []
        collaborator_ids = set(collaborators.ids)
        activity = []
        for message in self._get_public_ticket_messages(ticket):
            if not message.author_id or message.author_id.id not in collaborator_ids:
                continue
            summary = html2plaintext(message.body or "").strip()
            if not summary and message.attachment_ids:
                summary = _("Shared %s attachment(s).") % len(message.attachment_ids)
            if not summary and message.tracking_value_ids:
                summary = _("Updated ticket fields.")
            summary = " ".join(summary.split())
            if len(summary) > 180:
                summary = "%s..." % summary[:177]
            role = (
                _("Primary Contact")
                if ticket.partner_id and message.author_id.id == ticket.partner_id.id
                else _("Collaborator")
            )
            activity.append(
                {
                    "date": message.date,
                    "actor": message.author_id.name or _("Unknown"),
                    "role": role,
                    "detail": summary or _("Update received from portal."),
                    "kind": "message",
                }
            )
        if "communication_log_ids" in ticket._fields:
            logs = ticket.communication_log_ids.sudo().filtered(
                lambda log: (
                    log.logged_at
                    and log.channel == "portal"
                    and log.communication_type == "notification"
                    and (
                        "collaborator" in (log.subject or "").lower()
                        or "collaborator" in (log.summary or "").lower()
                        or "preference" in (log.subject or "").lower()
                    )
                )
            )
            for log in logs:
                activity.append(
                    {
                        "date": log.logged_at,
                        "actor": log.user_id.name or _("System"),
                        "role": _("System"),
                        "detail": (log.summary or log.subject or "").strip()
                        or _("Portal preference updated."),
                        "kind": "log",
                    }
                )
        activity.sort(key=lambda row: row["date"] or fields.Datetime.now(), reverse=True)
        return activity[:limit]

    def _prepare_public_ticket_values(self, ticket, **kwargs):
        public_files = self._get_public_ticket_attachments(ticket)
        public_image_files = public_files.filtered(
            lambda attachment: (attachment.mimetype or "").startswith("image/")
        )
        max_attachment_mb = (
            ticket._get_public_portal_max_attachment_bytes() / (1024 * 1024)
        )
        values = self._ticket_get_page_view_values(ticket, ticket.access_token, **kwargs)
        values.update(
            {
                "closed_stages": ticket.team_id._get_applicable_stages().filtered(
                    lambda stage: stage.close_from_portal
                ),
                "public_files": public_files,
                "public_image_files": public_image_files,
                "public_other_files": public_files - public_image_files,
                "public_messages": self._get_public_ticket_messages(ticket),
                "public_timeline": ticket._get_public_portal_timeline(),
                "public_collaborator_activity": self._get_public_collaborator_activity(ticket),
                "public_portal_url": ticket.public_portal_url,
                "public_rating_token": ticket.public_portal_rating_token,
                "pending_rating": ticket.public_portal_has_pending_rating,
                "can_reopen": ticket.public_portal_can_reopen,
                "can_escalate": ticket.public_portal_can_escalate,
                "allowed_extensions": ", ".join(
                    sorted(ticket._get_public_portal_allowed_extensions())
                ),
                "max_attachment_mb": f"{max_attachment_mb:.1f}",
                "public_db_name": request.env.cr.dbname,
                "reply_impact_options": self.PUBLIC_REPLY_IMPACT_OPTIONS,
                "reply_urgency_options": self.PUBLIC_REPLY_URGENCY_OPTIONS,
                "reopen_reason_options": ticket._get_public_portal_reopen_reason_selection(),
                "escalation_channel_options": ticket._get_public_portal_escalation_channel_selection(),
                "digest_options": ticket._get_public_portal_digest_selection(),
                "digest_policy": ticket._get_public_portal_digest_policy(),
                "digest_policy_locked": ticket._is_public_portal_digest_policy_locked(),
                "effective_digest_mode": ticket._get_public_portal_effective_digest_mode(),
                "public_collaborators": ticket._get_public_portal_collaborators(),
                "low_rating_max": self.LOW_RATING_MAX,
                "page_name": "ticket_public",
            }
        )
        return values

    def _redirect_public_ticket(self, ticket, **params):
        params.setdefault("db", request.env.cr.dbname)
        query = werkzeug.urls.url_encode(
            {key: value for key, value in params.items() if value not in (False, None, "")}
        )
        url = f"/helpdesk/track/{ticket.public_portal_token}"
        if query:
            url = f"{url}?{query}"
        return request.redirect(url)

    def _autoupdate_ticket_stage_from_public_reply(self, ticket):
        if (
            ticket.team_id.autoupdate_ticket_stage
            and ticket.team_id.autopupdate_dest_stage_id
            and ticket.stage_id in ticket.team_id.autopupdate_src_stage_ids
        ):
            ticket.stage_id = ticket.team_id.autopupdate_dest_stage_id.id

    def _create_public_reply_attachments(self, ticket, files):
        attachment_model = request.env["ir.attachment"].sudo()
        attachments = attachment_model
        for uploaded_file in files:
            if not uploaded_file or not uploaded_file.filename:
                continue
            data = uploaded_file.read()
            validation_error = ticket._validate_public_portal_attachment(
                uploaded_file.filename, len(data)
            )
            if validation_error:
                return attachment_model, validation_error
            attachments += attachment_model.create(
                {
                    "name": uploaded_file.filename,
                    "datas": base64.b64encode(data),
                    "res_model": "helpdesk.ticket",
                    "res_id": ticket.id,
                }
            )
        attachments.generate_access_token()
        return attachments, False

    @http.route(
        ["/helpdesk/track/<string:token>"], type="http", auth="public", website=True
    )
    def public_ticket_page(self, token, **kwargs):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        ticket._register_public_portal_visit()
        values = self._prepare_public_ticket_values(ticket, **kwargs)
        return request.render("helpdesk_custom_portal.public_helpdesk_ticket_page", values)

    @http.route(
        ["/helpdesk/track/<string:token>/reply"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_reply(self, token, message=None, **kwargs):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        impact_level = (kwargs.get("impact_level") or "").strip().lower()
        urgency_level = (kwargs.get("urgency_level") or "").strip().lower()
        change_summary = (kwargs.get("change_summary") or "").strip()
        collaborator_emails = (kwargs.get("collaborator_emails") or "").strip()

        impact_map = self._public_reply_impact_map()
        urgency_map = self._public_reply_urgency_map()
        if impact_level and impact_level not in impact_map:
            return self._redirect_public_ticket(
                ticket, reply_error=_("Selected impact level is invalid.")
            )
        if urgency_level and urgency_level not in urgency_map:
            return self._redirect_public_ticket(
                ticket, reply_error=_("Selected urgency level is invalid.")
            )

        attachments, error = self._create_public_reply_attachments(
            ticket, request.httprequest.files.getlist("attachment")
        )
        if error:
            return self._redirect_public_ticket(ticket, reply_error=error)

        collaborator_result = {
            "added_partners": request.env["res.partner"],
            "existing_partners": ticket.public_portal_collaborator_ids,
            "missing_emails": [],
        }
        if collaborator_emails:
            collaborator_result = ticket._update_public_portal_collaborators(
                collaborator_emails
            )

        message = (message or "").strip()
        if not any(
            [
                message,
                attachments,
                change_summary,
                impact_level,
                urgency_level,
                collaborator_emails,
            ]
        ):
            return self._redirect_public_ticket(
                ticket, reply_error=_("Add a message or at least one attachment.")
            )

        body_lines = []
        if message:
            body_lines.append(message)
        if impact_level:
            body_lines.append(_("Impact: %s") % impact_map[impact_level])
        if urgency_level:
            body_lines.append(_("Urgency: %s") % urgency_map[urgency_level])
        if change_summary:
            body_lines.append(_("What changed since last update:\n%s") % change_summary)
        if collaborator_result["added_partners"]:
            collaborator_names = ", ".join(
                collaborator_result["added_partners"].mapped("name")
            )
            body_lines.append(_("Collaborators added: %s") % collaborator_names)
        body = (
            plaintext2html("\n\n".join(body_lines))
            if body_lines
            else _("<p>Files shared from portal.</p>")
        )
        posted_message = ticket.message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=ticket.partner_id.id if ticket.partner_id else False,
            attachment_ids=attachments.ids,
        )
        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="customer_update",
                status="done",
                subject=_("Portal reply received"),
                summary=(
                    message
                    or change_summary
                    or _("Customer shared files from the public portal.")
                ),
                body="\n\n".join(
                    line
                    for line in [
                        message,
                        _("Impact: %s") % impact_map[impact_level]
                        if impact_level
                        else False,
                        _("Urgency: %s") % urgency_map[urgency_level]
                        if urgency_level
                        else False,
                        _("What changed since last update:\n%s") % change_summary
                        if change_summary
                        else False,
                    ]
                    if line
                )
                or _("Files shared from portal."),
                partner=ticket.partner_id,
                source_model=posted_message._name,
                source_res_id=posted_message.id,
            )
            if collaborator_result["added_partners"] or collaborator_result["missing_emails"]:
                collaborator_lines = []
                if collaborator_result["added_partners"]:
                    collaborator_lines.append(
                        _("Added collaborators: %s")
                        % ", ".join(collaborator_result["added_partners"].mapped("name"))
                    )
                if collaborator_result["missing_emails"]:
                    collaborator_lines.append(
                        _("Missing collaborator contacts: %s")
                        % ", ".join(collaborator_result["missing_emails"])
                    )
                ticket._create_communication_log(
                    channel="portal",
                    direction="inbound",
                    communication_type="notification",
                    status="done",
                    subject=_("Portal collaborator update"),
                    summary=_("Collaborator list changed from portal update."),
                    body="\n".join(collaborator_lines),
                    partner=ticket.partner_id,
                    source_model=posted_message._name,
                    source_res_id=posted_message.id,
                )
        self._autoupdate_ticket_stage_from_public_reply(ticket)
        warning_message = False
        if collaborator_result["missing_emails"]:
            warning_message = _(
                "Some collaborator emails were not found in your company contacts: %s"
            ) % ", ".join(collaborator_result["missing_emails"])
        return self._redirect_public_ticket(
            ticket,
            reply_success=1,
            reply_warning=warning_message,
        )

    @http.route(
        ["/helpdesk/track/<string:token>/close"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_close(self, token, stage_id=None, confirm_resolved=None, **kwargs):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        if str(confirm_resolved or "").lower() not in {"1", "true", "on", "yes"}:
            return self._redirect_public_ticket(
                ticket,
                close_error=_(
                    "Please confirm that the issue is resolved before closing the ticket."
                ),
            )
        stage = request.env["helpdesk.ticket.stage"].sudo().browse(int(stage_id or 0))
        allowed_stages = ticket.team_id._get_applicable_stages().filtered(
            lambda stage_record: stage_record.close_from_portal
        )
        if stage not in allowed_stages:
            return self._redirect_public_ticket(
                ticket, close_error=_("Selected close action is not allowed.")
            )
        ticket.with_context(skip_csat_resolution_validation=True).stage_id = stage.id
        ticket._touch_public_portal_customer_update()
        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="close_request",
                status="done",
                subject=_("Portal close request"),
                summary=_("Customer closed the ticket from the public portal."),
                body=_("Customer selected '%s' from the public portal.") % stage.name,
                partner=ticket.partner_id,
                source_model=ticket._name,
                source_res_id=ticket.id,
            )
        return self._redirect_public_ticket(ticket, close_success=1)

    @http.route(
        ["/helpdesk/track/<string:token>/reopen"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_reopen(
        self,
        token,
        reopen_reason=None,
        reopen_detail=None,
        confirm_reopen=None,
        **kwargs,
    ):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        reopen_reason = (reopen_reason or "").strip()
        reopen_detail = (reopen_detail or "").strip()
        if str(confirm_reopen or "").lower() not in {"1", "true", "on", "yes"}:
            return self._redirect_public_ticket(
                ticket, reopen_error=_("Please confirm reopen action.")
            )
        reason_map = ticket._get_public_portal_reopen_reason_map()
        if not reopen_reason:
            return self._redirect_public_ticket(
                ticket, reopen_error=_("Please select the reason for reopening this ticket.")
            )
        if reopen_reason not in reason_map:
            return self._redirect_public_ticket(
                ticket, reopen_error=_("Selected reopen reason is invalid.")
            )
        reopen_stage = ticket._get_public_portal_reopen_stage()
        if not ticket.public_portal_can_reopen or not reopen_stage:
            return self._redirect_public_ticket(
                ticket, reopen_error=_("This ticket cannot be reopened from the portal.")
            )
        ticket.write(
            {
                "stage_id": reopen_stage.id,
                "closed_date": False,
                "public_portal_last_reopen_reason": reopen_reason,
                "public_portal_last_reopen_detail": reopen_detail or False,
                "public_portal_last_reopen_at": fields.Datetime.now(),
            }
        )
        reopen_message = _("Ticket reopened by customer from public portal.")
        reopen_message += _("\nReason: %s") % reason_map[reopen_reason]
        if reopen_detail:
            reopen_message += _("\nDetail: %s") % reopen_detail
        posted_message = ticket.message_post(
            body=plaintext2html(reopen_message),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=ticket.partner_id.id if ticket.partner_id else False,
        )
        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="reopen_request",
                status="done",
                subject=_("Portal reopen request"),
                summary=_("Reopen reason: %s") % reason_map[reopen_reason],
                body=reopen_message,
                partner=ticket.partner_id,
                source_model=posted_message._name,
                source_res_id=posted_message.id,
            )
        return self._redirect_public_ticket(ticket, reopen_success=1)

    @http.route(
        ["/helpdesk/track/<string:token>/escalate"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_escalate(
        self,
        token,
        escalation_reason=None,
        preferred_channel=None,
        preferred_callback_at=None,
        confirm_escalation=None,
        **kwargs,
    ):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        if not ticket.public_portal_can_escalate:
            return self._redirect_public_ticket(
                ticket,
                escalation_error=_("Escalation request is not available for this ticket."),
            )
        if not self._is_truthy(confirm_escalation):
            return self._redirect_public_ticket(
                ticket,
                escalation_error=_("Please confirm escalation request."),
            )
        escalation_allowed, remaining_minutes = ticket._is_public_portal_escalation_allowed()
        if not escalation_allowed:
            return self._redirect_public_ticket(
                ticket,
                escalation_error=_(
                    "Escalation was requested recently. Please wait %s minute(s) before sending another request."
                )
                % remaining_minutes,
            )
        escalation_reason = (escalation_reason or "").strip()
        if not escalation_reason:
            return self._redirect_public_ticket(
                ticket,
                escalation_error=_("Please provide escalation reason."),
            )
        preferred_channel = (preferred_channel or "").strip()
        channel_map = ticket._get_public_portal_escalation_channel_map()
        if preferred_channel and preferred_channel not in channel_map:
            return self._redirect_public_ticket(
                ticket, escalation_error=_("Selected escalation channel is invalid.")
            )
        callback_dt = False
        if preferred_callback_at:
            callback_raw = str(preferred_callback_at).strip().replace("T", " ")
            try:
                callback_dt = fields.Datetime.to_datetime(callback_raw)
            except Exception:  # pragma: no cover - defensive parser
                callback_dt = False
            if callback_dt and callback_dt < fields.Datetime.now():
                return self._redirect_public_ticket(
                    ticket,
                    escalation_error=_(
                        "Preferred callback time cannot be in the past."
                    ),
                )

        write_vals = {
            "public_portal_last_escalation_reason": escalation_reason,
            "public_portal_last_escalation_channel": preferred_channel or False,
            "public_portal_last_escalation_callback_at": callback_dt or False,
            "public_portal_last_escalation_at": fields.Datetime.now(),
            "public_portal_escalation_count": ticket.public_portal_escalation_count + 1,
        }
        if "escalated" in ticket._fields:
            write_vals["escalated"] = True
        escalation_stage = ticket._get_public_portal_escalation_stage()
        if escalation_stage:
            write_vals["stage_id"] = escalation_stage.id
        ticket.write(write_vals)

        escalation_lines = [_("Escalation requested by customer from public portal.")]
        escalation_lines.append(_("Reason: %s") % escalation_reason)
        if preferred_channel:
            escalation_lines.append(
                _("Preferred channel: %s") % channel_map.get(preferred_channel)
            )
        if callback_dt:
            escalation_lines.append(
                _("Preferred callback time: %s")
                % fields.Datetime.to_string(callback_dt)
            )
        posted_message = ticket.message_post(
            body=plaintext2html("\n".join(escalation_lines)),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=ticket.partner_id.id if ticket.partner_id else False,
        )

        if ticket.user_id:
            try:
                pending_activity = request.env["mail.activity"].sudo().search(
                    [
                        ("res_model", "=", ticket._name),
                        ("res_id", "=", ticket.id),
                        ("user_id", "=", ticket.user_id.id),
                        ("summary", "=", _("Customer escalation request")),
                    ],
                    limit=1,
                )
                if not pending_activity:
                    ticket.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=ticket.user_id.id,
                        summary=_("Customer escalation request"),
                        note=_(
                            "Customer requested urgent escalation from public portal."
                        ),
                    )
            except Exception:
                pass

        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="status_change",
                status="done",
                subject=_("Portal escalation request"),
                summary=escalation_reason,
                body="\n".join(escalation_lines),
                partner=ticket.partner_id,
                source_model=posted_message._name,
                source_res_id=posted_message.id,
            )
        return self._redirect_public_ticket(ticket, escalation_success=1)

    @http.route(
        ["/helpdesk/track/<string:token>/preferences"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_preferences(
        self,
        token,
        digest_mode=None,
        remove_collaborator_id=None,
        **kwargs,
    ):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()

        has_preference_payload = self._is_truthy(kwargs.get("preferences_submit"))
        digest_mode = (digest_mode or "").strip()
        digest_map = ticket._get_public_portal_digest_map()
        digest_policy = ticket._get_public_portal_digest_policy()
        effective_digest_mode = ticket._get_public_portal_effective_digest_mode()
        write_vals = {}
        prefs_warning = False
        if has_preference_payload:
            if digest_policy == "ticket":
                if digest_mode not in digest_map:
                    return self._redirect_public_ticket(
                        ticket,
                        prefs_error=_("Selected notification frequency is invalid."),
                    )
            else:
                if digest_policy == "disabled":
                    prefs_warning = _(
                        "Digest mode is managed by support team policy and is currently disabled."
                    )
                elif effective_digest_mode in digest_map:
                    prefs_warning = _(
                        "Digest mode is managed by support team policy: %s."
                    ) % digest_map[effective_digest_mode]
            write_vals.update(
                {
                    "public_portal_notify_email": self._is_truthy(
                        kwargs.get("notify_email")
                    ),
                    "public_portal_notify_whatsapp": self._is_truthy(
                        kwargs.get("notify_whatsapp")
                    ),
                }
            )
            if digest_policy == "ticket":
                write_vals["public_portal_digest_mode"] = digest_mode

        collaborator_removed = False
        if remove_collaborator_id:
            try:
                partner_id = int(remove_collaborator_id)
            except (TypeError, ValueError):
                partner_id = 0
            partner = request.env["res.partner"].sudo().browse(partner_id)
            if not partner.exists() or partner not in ticket.public_portal_collaborator_ids:
                return self._redirect_public_ticket(
                    ticket,
                    prefs_error=_("Selected collaborator is no longer available."),
                )
            collaborator_removed = ticket._remove_public_portal_collaborator(partner)

        if write_vals:
            ticket.write(write_vals)

        if "communication_log_ids" in ticket._fields and (write_vals or collaborator_removed):
            body_lines = []
            if write_vals:
                digest_label = digest_map.get(
                    write_vals.get("public_portal_digest_mode")
                    or effective_digest_mode,
                    _("Disabled"),
                )
                body_lines.extend(
                    [
                        _("Email notifications: %s")
                        % (_("Enabled") if write_vals["public_portal_notify_email"] else _("Disabled")),
                        _("WhatsApp notifications: %s")
                        % (
                            _("Enabled")
                            if write_vals["public_portal_notify_whatsapp"]
                            else _("Disabled")
                        ),
                        _("Digest mode: %s") % digest_label,
                    ]
                )
            if collaborator_removed:
                body_lines.append(_("A portal collaborator was removed from this ticket."))
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="notification",
                status="done",
                subject=_("Portal notification preferences updated"),
                summary=_("Customer updated portal notification preferences."),
                body="\n".join(body_lines) or _("Portal preferences updated."),
                partner=ticket.partner_id,
                source_model=ticket._name,
                source_res_id=ticket.id,
            )
        return self._redirect_public_ticket(
            ticket,
            prefs_success=1,
            prefs_warning=prefs_warning,
        )

    @http.route(
        ["/helpdesk/track/<string:token>/rating"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_rating(self, token, rate=None, feedback=None, low_score_reason=None, **kwargs):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        if not ticket.public_portal_has_pending_rating or not ticket.public_portal_rating_token:
            return self._redirect_public_ticket(
                ticket, rating_error=_("This ticket does not have an active rating request.")
            )
        try:
            rate_value = int(rate or 0)
        except (TypeError, ValueError):
            rate_value = 0
        if rate_value < 1 or rate_value > 5:
            return self._redirect_public_ticket(
                ticket, rating_error=_("Please select a valid rating score.")
            )
        feedback = (feedback or "").strip()
        low_score_reason = (low_score_reason or "").strip()
        if rate_value <= self.LOW_RATING_MAX and not low_score_reason:
            return self._redirect_public_ticket(
                ticket,
                rating_error=_(
                    "Please provide the reason for low rating so we can improve follow-up."
                ),
            )
        compiled_feedback = feedback
        if low_score_reason:
            compiled_feedback = _("Low score reason: %s") % low_score_reason
            if feedback:
                compiled_feedback = "%s\n\n%s" % (compiled_feedback, feedback)
        ticket.sudo().rating_apply(
            rate_value,
            token=ticket.public_portal_rating_token,
            feedback=compiled_feedback or False,
        )
        ticket._touch_public_portal_customer_update()
        if "communication_log_ids" in ticket._fields:
            detail_lines = [_("Rating score: %s/5") % rate_value]
            if low_score_reason:
                detail_lines.append(_("Low score reason: %s") % low_score_reason)
            if feedback:
                detail_lines.append(_("Feedback: %s") % feedback)
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="feedback",
                status="done",
                subject=_("Portal CSAT submitted"),
                summary=_("Customer submitted a portal satisfaction rating."),
                body="\n".join(detail_lines),
                partner=ticket.partner_id,
                source_model=ticket._name,
                source_res_id=ticket.id,
            )
        return self._redirect_public_ticket(ticket, rating_success=1)

    @http.route(
        ["/helpdesk/track/<string:token>/feedback"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_feedback(self, token, feedback=None, **kwargs):
        if not self._is_portal_feature_enabled():
            return request.not_found()
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        feedback = (feedback or "").strip()
        if not feedback:
            return self._redirect_public_ticket(
                ticket, reply_error=_("Feedback message cannot be empty.")
            )
        posted_message = ticket.message_post(
            body=plaintext2html(f"[Portal Feedback]\n{feedback}"),
            message_type="comment",
            subtype_xmlid="mail.mt_comment",
            author_id=ticket.partner_id.id if ticket.partner_id else False,
        )
        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="portal",
                direction="inbound",
                communication_type="feedback",
                status="done",
                subject=_("Portal feedback received"),
                summary=feedback,
                body=feedback,
                partner=ticket.partner_id,
                source_model=posted_message._name,
                source_res_id=posted_message.id,
            )
        return self._redirect_public_ticket(ticket, feedback_success=1)

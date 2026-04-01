import base64
import secrets

from odoo import SUPERUSER_ID, _, fields, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools import plaintext2html


class HelpdeskCustomApiController(http.Controller):
    def _service_model(self, model_name):
        return request.env[model_name].sudo().with_user(SUPERUSER_ID)

    def _run_as_service_user(self):
        request.update_env(user=SUPERUSER_ID, su=True)

    def _params(self):
        return request.env["ir.config_parameter"].sudo()

    def _is_enabled(self):
        value = self._params().get_param("helpdesk_custom_api.enabled", default="True")
        return str(value).lower() not in {"0", "false", "no"}

    def _expected_token(self):
        return self._params().get_param("helpdesk_custom_api.token", default="")

    def _attachments_allowed(self):
        value = self._params().get_param(
            "helpdesk_custom_api.allow_attachment_upload", default="True"
        )
        return str(value).lower() not in {"0", "false", "no"}

    def _max_attachment_bytes(self):
        value = self._params().get_param("helpdesk_custom_api.max_attachment_mb", default="10")
        try:
            return int(float(value or 10) * 1024 * 1024)
        except (TypeError, ValueError):
            return 10 * 1024 * 1024

    def _default_team_id(self):
        value = self._params().get_param("helpdesk_custom_api.default_team_id", default="")
        try:
            return int(value)
        except (TypeError, ValueError):
            return False

    def _json(self, payload, status=200):
        return request.make_json_response(payload, status=status)

    def _error(self, code, message, status):
        return self._json({"ok": False, "error": {"code": code, "message": message}}, status=status)

    def _handle_exception(self, exc):
        if isinstance(exc, (ValueError, UserError, ValidationError)):
            return self._error("validation_error", str(exc), 400)
        return self._error("server_error", str(exc), 500)

    def _get_bearer_token(self):
        auth_header = request.httprequest.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return ""
        return auth_header[7:].strip()

    def _authorize(self):
        if not self._is_enabled():
            return self._error("api_disabled", _("Helpdesk API is disabled."), 503)
        expected = self._expected_token()
        provided = self._get_bearer_token()
        if not expected or not provided or not secrets.compare_digest(expected, provided):
            return self._error("unauthorized", _("Missing or invalid API token."), 401)
        return None

    def _payload(self):
        return request.httprequest.get_json(silent=True) or {}

    def _record_brief(self, record):
        return {"id": record.id, "name": record.display_name}

    def _to_int(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return False

    def _serialize_message(self, message):
        return {
            "id": message.id,
            "date": message.date.isoformat() if message.date else None,
            "author": message.author_id.name or message.email_from,
            "body": message.body or "",
            "message_type": message.message_type,
            "attachments": [
                {
                    "id": attachment.id,
                    "name": attachment.name,
                    "mimetype": attachment.mimetype,
                    "size": attachment.file_size,
                }
                for attachment in message.attachment_ids.sudo()
            ],
        }

    def _serialize_ticket(self, ticket, include_messages=False):
        ticket._ensure_public_portal_token()
        payload = {
            "id": ticket.id,
            "number": ticket.number,
            "name": ticket.name,
            "description": ticket.description or "",
            "priority": ticket.priority,
            "closed": bool(ticket.closed),
            "escalated": bool(getattr(ticket, "escalated", False)),
            "sla_expired": bool(getattr(ticket, "sla_expired", False)),
            "create_date": ticket.create_date.isoformat() if ticket.create_date else None,
            "assigned_date": ticket.assigned_date.isoformat() if ticket.assigned_date else None,
            "last_stage_update": (
                ticket.last_stage_update.isoformat() if ticket.last_stage_update else None
            ),
            "closed_date": ticket.closed_date.isoformat() if ticket.closed_date else None,
            "sla_deadline": ticket.sla_deadline.isoformat() if ticket.sla_deadline else None,
            "access_url": ticket.access_url,
            "public_portal_url": getattr(ticket, "public_portal_url", False),
            "team": self._record_brief(ticket.team_id) if ticket.team_id else None,
            "stage": self._record_brief(ticket.stage_id) if ticket.stage_id else None,
            "assigned_user": self._record_brief(ticket.user_id) if ticket.user_id else None,
            "partner": self._record_brief(ticket.partner_id) if ticket.partner_id else None,
            "category": self._record_brief(ticket.category_id) if ticket.category_id else None,
            "channel": self._record_brief(ticket.channel_id) if ticket.channel_id else None,
            "type": self._record_brief(ticket.type_id) if getattr(ticket, "type_id", False) else None,
            "sales_handoff_status": getattr(ticket, "sales_handoff_state", False),
        }
        if include_messages:
            messages = (
                ticket.message_ids.sudo()
                .filtered(lambda msg: msg.message_type in ("comment", "email", "notification"))
                .sorted("date", reverse=True)[:10]
            )
            payload["messages"] = [self._serialize_message(message) for message in messages]
        return payload

    def _serialize_dashboard(self, record):
        return {
            "scope_type": record.scope_type,
            "scope_name": record.scope_name,
            "team": self._record_brief(record.team_id) if record.team_id else None,
            "open_count": record.open_count,
            "closed_count": record.closed_count,
            "overdue_count": record.overdue_count,
            "escalated_count": record.escalated_count,
            "unassigned_count": record.unassigned_count,
            "high_priority_open_count": record.high_priority_open_count,
            "backlog_7d_count": record.backlog_7d_count,
            "backlog_30d_count": record.backlog_30d_count,
            "avg_assign_hours": record.avg_assign_hours,
            "avg_close_hours": record.avg_close_hours,
            "avg_rating": record.avg_rating,
            "breach_rate": record.breach_rate,
            "same_day_resolution_rate": record.same_day_resolution_rate,
            "assigned_within_4h_rate": record.assigned_within_4h_rate,
        }

    def _decode_attachments(self, ticket, attachments_payload):
        if not attachments_payload:
            return self._service_model("ir.attachment")
        if not self._attachments_allowed():
            raise ValueError(_("API attachment upload is disabled."))
        attachments = self._service_model("ir.attachment")
        max_size = self._max_attachment_bytes()
        for item in attachments_payload:
            filename = (item or {}).get("filename")
            content = (item or {}).get("content_base64")
            mimetype = (item or {}).get("mimetype")
            if not filename or not content:
                raise ValueError(_("Each attachment needs filename and content_base64."))
            try:
                raw = base64.b64decode(content)
            except Exception as exc:
                raise ValueError(_("Invalid attachment payload for %s.") % filename) from exc
            validation_error = False
            if hasattr(ticket, "_validate_public_portal_attachment"):
                validation_error = ticket._validate_public_portal_attachment(filename, len(raw))
            if validation_error:
                raise ValueError(validation_error)
            if len(raw) > max_size:
                raise ValueError(_("Attachment %s exceeds the configured size limit.") % filename)
            attachments += self._service_model("ir.attachment").create(
                {
                    "name": filename,
                    "datas": base64.b64encode(raw),
                    "res_model": "helpdesk.ticket",
                    "res_id": ticket.id,
                    "mimetype": mimetype,
                }
            )
        attachments.generate_access_token()
        return attachments

    def _ticket_domain_from_query(self):
        args = request.httprequest.args
        domain = []
        state = args.get("state")
        search = args.get("search")
        team_id = args.get("team_id")
        assigned_user_id = args.get("assigned_user_id")
        if state == "open":
            domain.append(("stage_id.closed", "=", False))
        elif state == "closed":
            domain.append(("stage_id.closed", "=", True))
        if args.get("overdue") in {"1", "true", "True"}:
            domain.append(("sla_expired", "=", True))
        if args.get("escalated") in {"1", "true", "True"}:
            domain.append(("escalated", "=", True))
        if team_id:
            domain.append(("team_id", "=", int(team_id)))
        if assigned_user_id:
            domain.append(("user_id", "=", int(assigned_user_id)))
        if search:
            domain.extend(["|", ("number", "ilike", search), ("name", "ilike", search)])
        return domain

    def _close_stage_for_ticket(self, ticket, stage_id=None):
        if stage_id:
            stage = request.env["helpdesk.ticket.stage"].sudo().browse(int(stage_id))
            if stage.exists():
                return stage
        applicable = (
            ticket.team_id._get_applicable_stages()
            if ticket.team_id
            else request.env["helpdesk.ticket.stage"].sudo().search([])
        )
        return applicable.filtered("closed")[:1]

    def _create_ticket_response(self, payload):
        self._run_as_service_user()
        name = (payload.get("name") or "").strip()
        description = (payload.get("description") or "").strip()
        if not name:
            return self._error("validation_error", _("Field 'name' is required."), 400)
        if not description:
            return self._error("validation_error", _("Field 'description' is required."), 400)

        env = request.env
        team_id = self._to_int(payload.get("team_id")) or self._default_team_id()
        values = {
            "name": name,
            "description": plaintext2html(description),
            "team_id": team_id or False,
            "partner_id": self._to_int(payload.get("partner_id")) or False,
            "partner_name": payload.get("partner_name"),
            "partner_email": payload.get("partner_email"),
            "category_id": self._to_int(payload.get("category_id")) or False,
            "channel_id": self._to_int(payload.get("channel_id"))
            or env.ref("helpdesk_mgmt.helpdesk_ticket_channel_web", raise_if_not_found=False).id,
            "priority": str(payload.get("priority", "1")),
            "user_id": self._to_int(payload.get("user_id")) or False,
        }
        if "type_id" in env["helpdesk.ticket"]._fields:
            values["type_id"] = self._to_int(payload.get("type_id")) or False
        ticket = env["helpdesk.ticket"].sudo().with_user(SUPERUSER_ID).create(values)
        attachments_payload = payload.get("attachments") or []
        try:
            attachments = self._decode_attachments(ticket, attachments_payload)
        except ValueError as exc:
            ticket.unlink()
            return self._error("validation_error", str(exc), 400)
        if "communication_log_ids" in ticket._fields:
            ticket._create_communication_log(
                channel="api",
                direction="inbound",
                communication_type="customer_update",
                status="done",
                subject=_("Ticket created via API"),
                summary=name,
                body=description,
                partner=ticket.partner_id,
                user=request.env.user,
                source_model=ticket._name,
                source_res_id=ticket.id,
            )
            if attachments:
                ticket._create_communication_log(
                    channel="api",
                    direction="inbound",
                    communication_type="customer_update",
                    status="done",
                    subject=_("API attachments uploaded"),
                    summary=_("%s attachment(s) uploaded during ticket creation.") % len(attachments),
                    body=_("Ticket creation included %s attachment(s).") % len(attachments),
                    partner=ticket.partner_id,
                    user=request.env.user,
                    source_model=ticket._name,
                    source_res_id=ticket.id,
                )
        return self._json(
            {"ok": True, "data": self._serialize_ticket(ticket, include_messages=True)},
            status=201,
        )

    @http.route("/api/helpdesk/v1/health", type="http", auth="none", methods=["GET"], csrf=False)
    def health(self, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        return self._json(
            {
                "ok": True,
                "data": {
                    "service": "helpdesk_custom_api",
                    "version": "v1",
                    "database": request.env.cr.dbname,
                    "server_time": fields.Datetime.to_string(fields.Datetime.now()),
                },
            }
        )

    @http.route("/api/helpdesk/v1/meta", type="http", auth="none", methods=["GET"], csrf=False)
    def meta(self, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        env = request.env
        data = {
            "teams": [
                {"id": team.id, "name": team.name}
                for team in env["helpdesk.ticket.team"].sudo().search([("active", "=", True)])
            ],
            "stages": [
                {"id": stage.id, "name": stage.name, "closed": bool(stage.closed)}
                for stage in env["helpdesk.ticket.stage"].sudo().search([])
            ],
            "categories": [
                {"id": category.id, "name": category.complete_name or category.name}
                for category in env["helpdesk.ticket.category"].sudo().search([("active", "=", True)])
            ],
            "channels": [
                {"id": channel.id, "name": channel.name}
                for channel in env["helpdesk.ticket.channel"].sudo().search([("active", "=", True)])
            ],
            "types": [
                {"id": ticket_type.id, "name": ticket_type.name}
                for ticket_type in env["helpdesk.ticket.type"].sudo().search([("active", "=", True)])
            ],
        }
        return self._json({"ok": True, "data": data})

    @http.route("/api/helpdesk/v1/tickets", type="http", auth="none", methods=["GET", "POST"], csrf=False)
    def tickets(self, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        try:
            if request.httprequest.method == "GET":
                args = request.httprequest.args
                limit = min(int(args.get("limit", 20)), 100)
                offset = max(int(args.get("offset", 0)), 0)
                domain = self._ticket_domain_from_query()
                Ticket = self._service_model("helpdesk.ticket")
                total = Ticket.search_count(domain)
                tickets = Ticket.search(
                    domain,
                    limit=limit,
                    offset=offset,
                    order="create_date desc, id desc",
                )
                return self._json(
                    {
                        "ok": True,
                        "data": {
                            "total": total,
                            "limit": limit,
                            "offset": offset,
                            "items": [self._serialize_ticket(ticket) for ticket in tickets],
                        },
                    }
                )

            return self._create_ticket_response(self._payload())
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route("/api/helpdesk/v1/tickets/create", type="http", auth="none", methods=["POST"], csrf=False)
    def create_ticket(self, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        try:
            return self._create_ticket_response(self._payload())
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route("/api/helpdesk/v1/tickets/<int:ticket_id>", type="http", auth="none", methods=["GET"], csrf=False)
    def get_ticket(self, ticket_id, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        ticket = request.env["helpdesk.ticket"].sudo().browse(ticket_id)
        if not ticket.exists():
            return self._error("not_found", _("Ticket not found."), 404)
        return self._json({"ok": True, "data": self._serialize_ticket(ticket, include_messages=True)})

    @http.route("/api/helpdesk/v1/tickets/<int:ticket_id>/reply", type="http", auth="none", methods=["POST"], csrf=False)
    def reply_ticket(self, ticket_id, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        try:
            self._run_as_service_user()
            ticket = self._service_model("helpdesk.ticket").browse(ticket_id)
            if not ticket.exists():
                return self._error("not_found", _("Ticket not found."), 404)
            payload = self._payload()
            message = (payload.get("message") or "").strip()
            attachments_payload = payload.get("attachments") or []
            try:
                attachments = self._decode_attachments(ticket, attachments_payload)
            except ValueError as exc:
                return self._error("validation_error", str(exc), 400)
            if not message and not attachments:
                return self._error(
                    "validation_error",
                    _("Reply must include a message or at least one attachment."),
                    400,
                )
            body = plaintext2html(message) if message else _("<p>Files shared via API.</p>")
            author_partner_id = (
                self._to_int(payload.get("author_partner_id")) or ticket.partner_id.id or False
            )
            posted_message = ticket.message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=author_partner_id,
                attachment_ids=attachments.ids,
            )
            if "communication_log_ids" in ticket._fields:
                ticket._create_communication_log(
                    channel="api",
                    direction="inbound",
                    communication_type="customer_update",
                    status="done",
                    subject=_("Reply received via API"),
                    summary=message or _("API caller shared attachments."),
                    body=message or _("Files shared via API."),
                    partner=request.env["res.partner"].sudo().browse(author_partner_id)
                    if author_partner_id
                    else ticket.partner_id,
                    user=request.env.user,
                    source_model=posted_message._name,
                    source_res_id=posted_message.id,
                )
            return self._json(
                {"ok": True, "data": self._serialize_ticket(ticket, include_messages=True)}
            )
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route("/api/helpdesk/v1/tickets/<int:ticket_id>/close", type="http", auth="none", methods=["POST"], csrf=False)
    def close_ticket(self, ticket_id, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        try:
            self._run_as_service_user()
            ticket = self._service_model("helpdesk.ticket").browse(ticket_id)
            if not ticket.exists():
                return self._error("not_found", _("Ticket not found."), 404)
            payload = self._payload()
            stage = self._close_stage_for_ticket(ticket, stage_id=payload.get("stage_id"))
            if not stage:
                return self._error(
                    "configuration_error",
                    _("No closed stage is available for this ticket."),
                    400,
                )
            close_vals = {"stage_id": stage.id}
            if "public_portal_resolution_summary" in ticket._fields:
                close_vals["public_portal_resolution_summary"] = (
                    payload.get("resolution_summary")
                    or _("Closed via API by integration process.")
                )
            ticket.write(close_vals)
            posted_message = ticket.message_post(
                body=_("Ticket closed from Helpdesk API."),
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
            )
            if "communication_log_ids" in ticket._fields:
                ticket._create_communication_log(
                    channel="api",
                    direction="inbound",
                    communication_type="close_request",
                    status="done",
                    subject=_("Ticket closed via API"),
                    summary=_("API caller closed the ticket."),
                    body=_("Ticket moved to closed stage '%s' via API.") % stage.name,
                    partner=ticket.partner_id,
                    user=request.env.user,
                    source_model=posted_message._name,
                    source_res_id=posted_message.id,
                )
            return self._json(
                {"ok": True, "data": self._serialize_ticket(ticket, include_messages=True)}
            )
        except Exception as exc:
            return self._handle_exception(exc)

    @http.route("/api/helpdesk/v1/tickets/<int:ticket_id>/close-action", type="http", auth="none", methods=["POST"], csrf=False)
    def close_ticket_action(self, ticket_id, **kwargs):
        return self.close_ticket(ticket_id, **kwargs)

    @http.route("/api/helpdesk/v1/kpi/summary", type="http", auth="none", methods=["GET"], csrf=False)
    def kpi_summary(self, **kwargs):
        auth_error = self._authorize()
        if auth_error:
            return auth_error
        Dashboard = request.env["helpdesk.ticket.kpi.dashboard"].sudo()
        overall = Dashboard.search([("scope_type", "=", "overall")], order="scope_sequence, id", limit=1)
        teams = Dashboard.search([("scope_type", "=", "team")], order="open_count desc, overdue_count desc")
        return self._json(
            {
                "ok": True,
                "data": {
                    "overall": self._serialize_dashboard(overall) if overall else None,
                    "teams": [self._serialize_dashboard(record) for record in teams],
                },
            }
        )

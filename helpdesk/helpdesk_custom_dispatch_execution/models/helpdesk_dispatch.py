from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HelpdeskDispatch(models.Model):
    _inherit = "helpdesk.dispatch"

    evidence_ids = fields.One2many(
        "helpdesk.dispatch.evidence",
        "dispatch_id",
        string="Execution Evidence",
    )
    evidence_count = fields.Integer(compute="_compute_execution_metrics", store=True)
    photo_evidence_count = fields.Integer(compute="_compute_execution_metrics", store=True)
    evidence_logged = fields.Boolean(compute="_compute_execution_metrics", store=True)
    travel_start_at = fields.Datetime(tracking=True)
    arrival_at = fields.Datetime(tracking=True)
    departure_at = fields.Datetime(tracking=True)
    travel_duration_hours = fields.Float(compute="_compute_execution_metrics", store=True)
    onsite_duration_hours = fields.Float(compute="_compute_execution_metrics", store=True)
    pre_departure_customer_confirmed = fields.Boolean(string="Customer Confirmed", tracking=True)
    pre_departure_tools_ready = fields.Boolean(string="Tools Ready", tracking=True)
    pre_departure_scope_confirmed = fields.Boolean(string="Scope Confirmed", tracking=True)
    pre_departure_asset_checked = fields.Boolean(string="Asset Verified", tracking=True)
    pre_departure_completion = fields.Integer(compute="_compute_execution_metrics", store=True)
    onsite_access_confirmed = fields.Boolean(string="Access Confirmed", tracking=True)
    onsite_issue_validated = fields.Boolean(string="Issue Validated", tracking=True)
    onsite_customer_briefed = fields.Boolean(string="Customer Briefed", tracking=True)
    onsite_work_documented = fields.Boolean(string="Work Documented", tracking=True)
    onsite_completion = fields.Integer(compute="_compute_execution_metrics", store=True)
    execution_completion = fields.Integer(compute="_compute_execution_metrics", store=True)
    ready_for_departure = fields.Boolean(compute="_compute_execution_metrics", store=True)
    ready_for_completion = fields.Boolean(compute="_compute_execution_metrics", store=True)
    evidence_required = fields.Boolean(
        compute="_compute_execution_requirements",
        store=True,
    )
    customer_signoff_required = fields.Boolean(default=True, tracking=True)
    signoff_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("signed", "Signed"),
            ("declined", "Declined"),
            ("not_required", "Not Required"),
        ],
        default="pending",
        required=True,
        tracking=True,
    )
    signoff_contact_name = fields.Char(tracking=True)
    signoff_contact_role = fields.Char(tracking=True)
    signoff_notes = fields.Text(tracking=True)
    signoff_at = fields.Datetime(tracking=True)
    latest_evidence_on = fields.Datetime(compute="_compute_execution_metrics", store=True)

    @api.depends("dispatch_type", "travel_required")
    def _compute_execution_requirements(self):
        required_types = {"onsite_visit", "inspection", "delivery"}
        for dispatch in self:
            dispatch.evidence_required = dispatch.travel_required or dispatch.dispatch_type in required_types

    @api.depends(
        "travel_start_at",
        "arrival_at",
        "departure_at",
        "evidence_ids",
        "evidence_ids.is_photo",
        "evidence_ids.captured_on",
        "pre_departure_customer_confirmed",
        "pre_departure_tools_ready",
        "pre_departure_scope_confirmed",
        "pre_departure_asset_checked",
        "onsite_access_confirmed",
        "onsite_issue_validated",
        "onsite_customer_briefed",
        "onsite_work_documented",
        "customer_signoff_required",
        "signoff_status",
        "evidence_required",
    )
    def _compute_execution_metrics(self):
        for dispatch in self:
            pre_departure_checks = [
                dispatch.pre_departure_customer_confirmed,
                dispatch.pre_departure_tools_ready,
                dispatch.pre_departure_scope_confirmed,
                dispatch.pre_departure_asset_checked,
            ]
            onsite_checks = [
                dispatch.onsite_access_confirmed,
                dispatch.onsite_issue_validated,
                dispatch.onsite_customer_briefed,
                dispatch.onsite_work_documented,
                bool(dispatch.evidence_ids),
            ]
            dispatch.pre_departure_completion = int(
                round((sum(bool(value) for value in pre_departure_checks) / len(pre_departure_checks)) * 100)
            )
            dispatch.onsite_completion = int(
                round((sum(bool(value) for value in onsite_checks) / len(onsite_checks)) * 100)
            )
            execution_values = pre_departure_checks + onsite_checks
            dispatch.execution_completion = int(
                round((sum(bool(value) for value in execution_values) / len(execution_values)) * 100)
            )
            dispatch.evidence_count = len(dispatch.evidence_ids)
            dispatch.photo_evidence_count = len(dispatch.evidence_ids.filtered("is_photo"))
            dispatch.evidence_logged = bool(dispatch.evidence_ids)
            dispatch.ready_for_departure = all(pre_departure_checks)
            signoff_ok = (
                not dispatch.customer_signoff_required
                or dispatch.signoff_status in {"signed", "declined", "not_required"}
            )
            evidence_ok = not dispatch.evidence_required or bool(dispatch.evidence_ids)
            dispatch.ready_for_completion = all(onsite_checks) and signoff_ok and evidence_ok
            dispatch.latest_evidence_on = max(dispatch.evidence_ids.mapped("captured_on"), default=False)

            dispatch.travel_duration_hours = 0.0
            if dispatch.travel_start_at and dispatch.arrival_at:
                start = fields.Datetime.to_datetime(dispatch.travel_start_at)
                end = fields.Datetime.to_datetime(dispatch.arrival_at)
                dispatch.travel_duration_hours = max((end - start).total_seconds() / 3600.0, 0.0)

            dispatch.onsite_duration_hours = 0.0
            onsite_end = dispatch.departure_at or dispatch.actual_end
            if dispatch.arrival_at and onsite_end:
                start = fields.Datetime.to_datetime(dispatch.arrival_at)
                end = fields.Datetime.to_datetime(onsite_end)
                dispatch.onsite_duration_hours = max((end - start).total_seconds() / 3600.0, 0.0)

    @api.onchange("customer_signoff_required")
    def _onchange_customer_signoff_required(self):
        for dispatch in self:
            if dispatch.customer_signoff_required and dispatch.signoff_status == "not_required":
                dispatch.signoff_status = "pending"
            if not dispatch.customer_signoff_required:
                dispatch.signoff_status = "not_required"

    def _raise_missing_items(self, title, items):
        if items:
            raise ValidationError(
                _("%(title)s: %(items)s") % {"title": title, "items": ", ".join(items)}
            )

    def _validate_pre_departure_requirements(self):
        for dispatch in self:
            missing = []
            if not dispatch.pre_departure_customer_confirmed:
                missing.append(_("customer confirmation"))
            if not dispatch.pre_departure_tools_ready:
                missing.append(_("tools readiness"))
            if not dispatch.pre_departure_scope_confirmed:
                missing.append(_("scope confirmation"))
            if not dispatch.pre_departure_asset_checked:
                missing.append(_("asset verification"))
            self._raise_missing_items(
                _("Complete the pre-departure checklist before starting travel"),
                missing,
            )

    def _validate_completion_requirements(self):
        for dispatch in self:
            missing = []
            if not dispatch.onsite_access_confirmed:
                missing.append(_("site access confirmation"))
            if not dispatch.onsite_issue_validated:
                missing.append(_("issue validation"))
            if not dispatch.onsite_customer_briefed:
                missing.append(_("customer briefing"))
            if not dispatch.onsite_work_documented:
                missing.append(_("work documentation"))
            if dispatch.evidence_required and not dispatch.evidence_ids:
                missing.append(_("at least one execution evidence item"))
            if dispatch.customer_signoff_required and dispatch.signoff_status not in {"signed", "declined"}:
                missing.append(_("customer sign-off decision"))
            self._raise_missing_items(
                _("Dispatch cannot be completed until execution controls are finished"),
                missing,
            )

    def _validate_report_submission_requirements(self):
        for dispatch in self:
            if dispatch.state not in {"completed", "no_access"}:
                raise ValidationError(
                    _("Dispatch %(name)s must be completed or marked no access before submitting the service report.")
                    % {"name": dispatch.display_name}
                )
            if dispatch.state == "no_access":
                if dispatch.pre_departure_completion < 100:
                    raise ValidationError(
                        _("Dispatch %(name)s still has an incomplete pre-departure checklist.")
                        % {"name": dispatch.display_name}
                    )
                continue
            dispatch._validate_completion_requirements()

    def action_mark_en_route(self):
        target = self.filtered(lambda rec: rec.state in {"draft", "scheduled"})
        target._validate_pre_departure_requirements()
        for dispatch in target:
            if not dispatch.travel_start_at:
                dispatch.travel_start_at = fields.Datetime.now()
        return super().action_mark_en_route()

    def action_check_in(self):
        target = self.filtered(lambda rec: rec.state in {"draft", "scheduled", "en_route"})
        result = super().action_check_in()
        for dispatch in target:
            values = {}
            if not dispatch.travel_start_at and dispatch.travel_required:
                values["travel_start_at"] = dispatch.actual_start or fields.Datetime.now()
            if not dispatch.arrival_at:
                values["arrival_at"] = fields.Datetime.now()
            if values:
                dispatch.write(values)
        return result

    def action_leave_site(self):
        for dispatch in self.filtered(lambda rec: rec.state == "on_site"):
            values = {"departure_at": dispatch.departure_at or fields.Datetime.now()}
            dispatch.write(values)
            dispatch.message_post(body=_("Engineer left the site and is preparing the wrap-up."))
            dispatch._post_ticket_message(_("Dispatch %(name)s has left the site and is pending wrap-up."))
        return True

    def action_mark_signoff_received(self):
        for dispatch in self:
            dispatch.write(
                {
                    "signoff_status": "signed",
                    "signoff_at": dispatch.signoff_at or fields.Datetime.now(),
                    "signoff_contact_name": dispatch.signoff_contact_name
                    or dispatch.site_contact_name
                    or dispatch.partner_id.name,
                }
            )
            dispatch.message_post(body=_("Customer sign-off recorded."))
        return True

    def action_mark_signoff_declined(self):
        for dispatch in self:
            dispatch.write(
                {
                    "signoff_status": "declined",
                    "signoff_at": dispatch.signoff_at or fields.Datetime.now(),
                    "signoff_contact_name": dispatch.signoff_contact_name
                    or dispatch.site_contact_name
                    or dispatch.partner_id.name,
                }
            )
            dispatch.message_post(body=_("Customer sign-off was declined or deferred."))
        return True

    def action_complete(self):
        target = self.filtered(lambda rec: rec.state in {"scheduled", "en_route", "on_site"})
        target._validate_completion_requirements()
        for dispatch in target:
            values = {}
            if not dispatch.departure_at:
                values["departure_at"] = fields.Datetime.now()
            if not dispatch.actual_end:
                values["actual_end"] = values.get("departure_at") or fields.Datetime.now()
            if values:
                dispatch.write(values)
        return super().action_complete()

    def action_mark_no_access(self):
        target = self.filtered(lambda rec: rec.state in {"scheduled", "en_route", "on_site"})
        for dispatch in target:
            if dispatch.pre_departure_completion < 100:
                dispatch._validate_pre_departure_requirements()
            values = {
                "departure_at": dispatch.departure_at or fields.Datetime.now(),
                "customer_signoff_required": False,
                "signoff_status": "not_required",
            }
            dispatch.write(values)
        return super().action_mark_no_access()

    def action_open_evidence(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_dispatch_execution.action_helpdesk_dispatch_evidence"
        )
        action["domain"] = [("dispatch_id", "=", self.id)]
        action["context"] = {
            "default_dispatch_id": self.id,
            "default_engineer_id": self.engineer_id.id or self.env.user.id,
            "search_default_dispatch_id": self.id,
        }
        return action

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HelpdeskFieldServiceReport(models.Model):
    _name = "helpdesk.field.service.report"
    _description = "Helpdesk Field Service Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "service_date desc, id desc"

    state_selection = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("acknowledged", "Acknowledged"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ]
    visit_outcome_selection = [
        ("resolved", "Resolved"),
        ("partial_restore", "Partial Restore"),
        ("follow_up", "Follow-up Required"),
        ("training", "Training / Handover"),
        ("no_access", "No Access"),
    ]

    name = fields.Char(required=True, tracking=True, default="New Service Report")
    dispatch_id = fields.Many2one(
        "helpdesk.dispatch",
        string="Dispatch",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    ticket_id = fields.Many2one(
        related="dispatch_id.ticket_id",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        related="dispatch_id.partner_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="dispatch_id.company_id",
        store=True,
        readonly=True,
    )
    team_id = fields.Many2one(
        related="dispatch_id.team_id",
        store=True,
        readonly=True,
    )
    engineer_id = fields.Many2one(
        related="dispatch_id.engineer_id",
        store=True,
        readonly=True,
    )
    dispatch_state = fields.Selection(
        related="dispatch_id.state",
        string="Dispatch State",
        store=True,
        readonly=True,
    )
    service_date = fields.Datetime(required=True, tracking=True, default=fields.Datetime.now)
    visit_outcome = fields.Selection(
        selection=visit_outcome_selection,
        default="follow_up",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=state_selection,
        default="draft",
        required=True,
        tracking=True,
    )
    executive_summary = fields.Html()
    issue_confirmed = fields.Boolean(tracking=True)
    environment_checked = fields.Boolean(tracking=True)
    logs_collected = fields.Boolean(tracking=True)
    customer_briefed = fields.Boolean(tracking=True)
    safety_check_completed = fields.Boolean(tracking=True)
    resolution_confirmed = fields.Boolean(tracking=True)
    checklist_completion = fields.Integer(
        compute="_compute_checklist_completion",
        store=True,
    )
    root_cause = fields.Text()
    actions_performed = fields.Html()
    parts_used = fields.Text()
    recommendations = fields.Text()
    followup_required = fields.Boolean(tracking=True)
    next_steps = fields.Text()
    customer_contact_name = fields.Char(string="Customer Contact", tracking=True)
    customer_contact_role = fields.Char(tracking=True)
    customer_feedback = fields.Text()
    customer_acknowledged = fields.Boolean(tracking=True)
    acknowledgement_date = fields.Datetime(tracking=True)
    customer_signature = fields.Binary(attachment=True)
    customer_signature_filename = fields.Char()
    internal_note = fields.Html()

    @api.depends(
        "issue_confirmed",
        "environment_checked",
        "logs_collected",
        "customer_briefed",
        "safety_check_completed",
        "resolution_confirmed",
    )
    def _compute_checklist_completion(self):
        for report in self:
            checks = [
                report.issue_confirmed,
                report.environment_checked,
                report.logs_collected,
                report.customer_briefed,
                report.safety_check_completed,
                report.resolution_confirmed,
            ]
            report.checklist_completion = int(
                round((sum(bool(value) for value in checks) / len(checks)) * 100)
            )

    @api.model
    def _ensure_report_feature_enabled(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.ops.field_service_report",
            message=_("Field service reporting is disabled in Helpdesk feature settings."),
        )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        self._ensure_report_feature_enabled()
        for vals in vals_list:
            if vals.get("dispatch_id"):
                dispatch = self.env["helpdesk.dispatch"].browse(vals["dispatch_id"])
                if not vals.get("name") or vals.get("name") == "New Service Report":
                    vals["name"] = _("%(dispatch)s Service Report") % {
                        "dispatch": dispatch.display_name,
                    }
                vals.setdefault(
                    "service_date",
                    dispatch.actual_end or dispatch.actual_start or dispatch.scheduled_end or dispatch.scheduled_start,
                )
                vals.setdefault("customer_contact_name", dispatch.site_contact_name)
                vals.setdefault("visit_outcome", self._default_outcome_for_dispatch(dispatch))
                vals.setdefault("followup_required", dispatch.followup_required)
                vals.setdefault("next_steps", dispatch.followup_action)
                vals.setdefault("actions_performed", dispatch.work_summary)
        return super().create(vals_list)

    @api.model
    def _default_outcome_for_dispatch(self, dispatch):
        if dispatch.state == "no_access":
            return "no_access"
        if dispatch.resolution_status == "resolved":
            return "resolved"
        if dispatch.resolution_status == "temporary_fix":
            return "partial_restore"
        return "follow_up"

    @api.constrains("customer_acknowledged", "acknowledgement_date")
    def _check_acknowledgement_date(self):
        for report in self:
            if report.customer_acknowledged and not report.acknowledgement_date:
                raise ValidationError(
                    _("Acknowledgement date is required once the customer acknowledgement is marked.")
                )

    def action_submit(self):
        self._ensure_report_feature_enabled()
        for report in self:
            if not report.executive_summary and not report.actions_performed:
                raise ValidationError(
                    _("Add an executive summary or documented actions before submitting the report.")
                )
            report.write({"state": "submitted"})
            report.message_post(body=_("Service report submitted for review."))
        return True

    def action_acknowledge(self):
        self._ensure_report_feature_enabled()
        for report in self:
            values = {
                "state": "acknowledged",
                "customer_acknowledged": True,
                "acknowledgement_date": report.acknowledgement_date or fields.Datetime.now(),
            }
            report.write(values)
            report.message_post(body=_("Customer acknowledgement recorded."))
        return True

    def action_close(self):
        self._ensure_report_feature_enabled()
        self.write({"state": "closed"})
        self.message_post(body=_("Service report closed."))
        return True

    def action_reset_draft(self):
        self._ensure_report_feature_enabled()
        self.write({"state": "draft"})
        self.message_post(body=_("Service report reset to draft."))
        return True

    def action_cancel(self):
        self._ensure_report_feature_enabled()
        self.write({"state": "cancelled"})
        self.message_post(body=_("Service report cancelled."))
        return True

    def action_open_dispatch(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dispatch"),
            "res_model": "helpdesk.dispatch",
            "view_mode": "form",
            "res_id": self.dispatch_id.id,
        }

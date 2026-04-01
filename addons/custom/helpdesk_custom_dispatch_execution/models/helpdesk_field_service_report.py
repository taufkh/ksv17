from odoo import _, fields, models
from odoo.exceptions import ValidationError


class HelpdeskFieldServiceReport(models.Model):
    _inherit = "helpdesk.field.service.report"

    dispatch_execution_completion = fields.Integer(
        related="dispatch_id.execution_completion",
        string="Execution Completion",
        store=True,
        readonly=True,
    )
    dispatch_pre_departure_completion = fields.Integer(
        related="dispatch_id.pre_departure_completion",
        string="Pre-Departure Completion",
        store=True,
        readonly=True,
    )
    dispatch_onsite_completion = fields.Integer(
        related="dispatch_id.onsite_completion",
        string="On-Site Completion",
        store=True,
        readonly=True,
    )
    dispatch_evidence_count = fields.Integer(
        related="dispatch_id.evidence_count",
        string="Evidence Count",
        store=True,
        readonly=True,
    )
    dispatch_signoff_status = fields.Selection(
        related="dispatch_id.signoff_status",
        string="Sign-off Status",
        store=True,
        readonly=True,
    )
    dispatch_travel_duration_hours = fields.Float(
        related="dispatch_id.travel_duration_hours",
        string="Travel Hours",
        store=True,
        readonly=True,
    )
    dispatch_onsite_duration_hours = fields.Float(
        related="dispatch_id.onsite_duration_hours",
        string="On-Site Hours",
        store=True,
        readonly=True,
    )

    def action_submit(self):
        for report in self:
            if not report.dispatch_id:
                raise ValidationError(_("A dispatch is required before submitting the service report."))
            report.dispatch_id._validate_report_submission_requirements()
        return super().action_submit()

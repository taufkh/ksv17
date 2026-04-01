from odoo import _, api, fields, models


class HelpdeskDispatchEvidence(models.Model):
    _name = "helpdesk.dispatch.evidence"
    _description = "Helpdesk Dispatch Evidence"
    _order = "captured_on desc, id desc"

    evidence_type_selection = [
        ("arrival_photo", "Arrival Photo"),
        ("site_access", "Site Access Proof"),
        ("work_in_progress", "Work In Progress"),
        ("completion_photo", "Completion Photo"),
        ("customer_signoff", "Customer Sign-off"),
        ("document", "Document"),
        ("other", "Other"),
    ]
    capture_stage_selection = [
        ("pre_departure", "Pre-Departure"),
        ("arrival", "Arrival"),
        ("on_site", "On Site"),
        ("departure", "Departure"),
        ("signoff", "Sign-off"),
    ]

    name = fields.Char(required=True)
    dispatch_id = fields.Many2one(
        "helpdesk.dispatch",
        required=True,
        ondelete="cascade",
        index=True,
    )
    ticket_id = fields.Many2one(related="dispatch_id.ticket_id", store=True, readonly=True)
    partner_id = fields.Many2one(related="dispatch_id.partner_id", store=True, readonly=True)
    engineer_id = fields.Many2one(
        "res.users",
        string="Captured By",
        default=lambda self: self.env.user,
        required=True,
    )
    evidence_type = fields.Selection(
        selection=evidence_type_selection,
        default="work_in_progress",
        required=True,
    )
    capture_stage = fields.Selection(
        selection=capture_stage_selection,
        default="on_site",
        required=True,
    )
    captured_on = fields.Datetime(required=True, default=fields.Datetime.now)
    file_data = fields.Binary(required=True, attachment=True)
    file_name = fields.Char(required=True)
    note = fields.Text()
    is_photo = fields.Boolean(compute="_compute_is_photo", store=True)

    @api.depends("evidence_type")
    def _compute_is_photo(self):
        photo_types = {"arrival_photo", "site_access", "work_in_progress", "completion_photo", "customer_signoff"}
        for evidence in self:
            evidence.is_photo = evidence.evidence_type in photo_types

    @api.model_create_multi
    def create(self, vals_list):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.ops.dispatch_execution",
            message=_("Dispatch execution is disabled in Helpdesk feature settings."),
        )
        return super().create(vals_list)

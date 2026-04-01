from odoo import _, api, fields, models


class HelpdeskDispatch(models.Model):
    _inherit = "helpdesk.dispatch"

    service_report_ids = fields.One2many(
        "helpdesk.field.service.report",
        "dispatch_id",
        string="Service Reports",
    )
    service_report_count = fields.Integer(
        compute="_compute_service_report_summary",
        store=True,
    )
    latest_service_report_state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("acknowledged", "Acknowledged"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_service_report_summary",
        store=True,
    )
    customer_acknowledged_report = fields.Boolean(
        compute="_compute_service_report_summary",
        store=True,
    )

    @api.depends(
        "service_report_ids",
        "service_report_ids.state",
        "service_report_ids.customer_acknowledged",
        "service_report_ids.service_date",
    )
    def _compute_service_report_summary(self):
        for dispatch in self:
            reports = dispatch.service_report_ids.sorted(
                key=lambda report: report.service_date or fields.Datetime.now(),
                reverse=True,
            )
            dispatch.service_report_count = len(reports)
            dispatch.latest_service_report_state = reports[:1].state if reports else False
            dispatch.customer_acknowledged_report = any(
                report.customer_acknowledged for report in reports
            )

    def action_create_service_report(self):
        self.ensure_one()
        draft_report = self.service_report_ids.filtered(lambda report: report.state == "draft")[:1]
        report = draft_report or self.env["helpdesk.field.service.report"].create(
            {
                "dispatch_id": self.id,
                "executive_summary": self.work_summary,
                "customer_contact_name": self.site_contact_name,
                "service_date": self.actual_end
                or self.actual_start
                or self.scheduled_end
                or self.scheduled_start
                or fields.Datetime.now(),
                "root_cause": self.followup_action if self.state == "no_access" else False,
                "followup_required": self.followup_required,
                "next_steps": self.followup_action,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Field Service Report"),
            "res_model": "helpdesk.field.service.report",
            "view_mode": "form",
            "res_id": report.id,
        }

    def action_open_service_reports(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_field_service_report.action_helpdesk_field_service_report"
        )
        action["domain"] = [("dispatch_id", "=", self.id)]
        action["context"] = {
            "default_dispatch_id": self.id,
            "search_default_dispatch_id": self.id,
        }
        return action

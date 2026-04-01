from odoo import _, models


class HelpdeskServiceReviewPackReport(models.AbstractModel):
    _name = "report.helpdesk_custom_service_review_pack.srp_report"
    _description = "Helpdesk Service Review Pack Report"

    def _get_report_values(self, docids, data=None):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.review.pack",
            message=_("Service review packs are disabled in Helpdesk feature settings."),
        )
        docs = self.env["helpdesk.service.review.pack"].browse(docids)
        return {
            "doc_ids": docs.ids,
            "doc_model": "helpdesk.service.review.pack",
            "docs": docs,
            "data": data or {},
        }

from odoo import http
from odoo.http import content_disposition, request


class BrownielabStockCountImportController(http.Controller):
    @http.route(
        "/brownielab_stock_count_import/template/<int:wizard_id>",
        type="http",
        auth="user",
    )
    def download_template(self, wizard_id, **kwargs):
        wizard = request.env["brownielab.stock.count.import.wizard"].browse(wizard_id)
        if not wizard.exists():
            return request.not_found()
        wizard.check_access_rights("read")
        wizard.check_access_rule("read")
        content = wizard._build_template_xlsx()
        filename = "brownielab_stock_count_template.xlsx"
        return request.make_response(
            content,
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

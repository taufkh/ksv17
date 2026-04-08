from odoo import http
from odoo.http import content_disposition, request


class PosSalesSimulationController(http.Controller):
    @http.route(
        "/pos_sales_simulation/<int:simulation_id>/xlsx",
        type="http",
        auth="user",
    )
    def download_xlsx(self, simulation_id, **kwargs):
        simulation = request.env["pos.sales.simulation"].browse(simulation_id)
        simulation.check_access_rights("read")
        simulation.check_access_rule("read")
        if not simulation.exists():
            return request.not_found()

        xlsx_data, filename = simulation._build_xlsx_file()
        return request.make_response(
            xlsx_data,
            headers=[
                (
                    "Content-Type",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

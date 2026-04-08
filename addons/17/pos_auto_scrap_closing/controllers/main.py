from odoo import http
from odoo.http import request
from odoo.tools.misc import file_path


class PosAutoScrapClosingController(http.Controller):
    @http.route("/pos_auto_scrap_closing/icon.png", type="http", auth="none")
    def module_icon(self):
        icon_path = file_path("pos_auto_scrap_closing/static/description/icon.png")
        with open(icon_path, "rb") as image_file:
            image_data = image_file.read()
        return request.make_response(
            image_data,
            headers=[
                ("Content-Type", "image/png"),
                ("Cache-Control", "public, max-age=86400"),
            ],
        )

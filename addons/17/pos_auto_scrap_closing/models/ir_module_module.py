import base64

from odoo import models
from odoo.modules.module import get_module_resource


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def _get_icon_image(self):
        super()._get_icon_image()
        icon_path = get_module_resource(
            "pos_auto_scrap_closing", "static", "description", "icon.png"
        )
        if not icon_path:
            return

        target_modules = self.filtered(
            lambda module: module.name == "pos_auto_scrap_closing" and not module.icon_image
        )
        if not target_modules:
            return

        with open(icon_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read())
        for module in target_modules:
            module.icon_image = image_data

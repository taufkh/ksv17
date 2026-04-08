import base64

from odoo import api, models
from odoo.modules.module import get_module_resource


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    @api.model
    def _set_pos_auto_scrap_icon_url(self):
        module = self.sudo().search([("name", "=", "pos_auto_scrap_closing")], limit=1)
        if not module:
            return False
        icon_path = get_module_resource(
            "pos_auto_scrap_closing", "static", "description", "icon.png"
        )
        if not icon_path:
            return False
        with open(icon_path, "rb") as image_file:
            icon_value = "data:image/png;base64,%s" % base64.b64encode(image_file.read()).decode()
        if module.icon != icon_value:
            module.icon = icon_value
        return True

    @api.model
    def update_list(self):
        result = super().update_list()
        self._set_pos_auto_scrap_icon_url()
        return result

    def write(self, vals):
        result = super().write(vals)
        if "icon" in vals:
            target_modules = self.filtered(
                lambda module: (
                    module.name == "pos_auto_scrap_closing"
                    and (module.icon or "").startswith("/pos_auto_scrap_closing/")
                )
            )
            if target_modules:
                self._set_pos_auto_scrap_icon_url()
        return result

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

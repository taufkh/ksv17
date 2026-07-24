from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def action_open_brownielab_stock_count_import(self):
        action = self.env.ref(
            "brownielab_stock_count_import.action_brownielab_stock_count_import_wizard"
        ).read()[0]
        default_location_id = False
        locations = self.mapped("location_id").filtered(lambda location: location.usage == "internal")
        if len(locations) == 1:
            default_location_id = locations.id
        action["context"] = {
            **self.env.context,
            "default_location_id": default_location_id,
        }
        return action

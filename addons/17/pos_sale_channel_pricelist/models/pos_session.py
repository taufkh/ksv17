from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_sale_channel_pricelist_ids(self):
        self.ensure_one()
        channels = self.env["pos.sale.channel"].search(
            [
                ("active", "=", True),
                ("pricelist_id", "!=", False),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return channels.mapped("pricelist_id").ids

    def _loader_params_pos_sale_channel(self):
        result = super()._loader_params_pos_sale_channel()
        fields = result["search_params"].setdefault("fields", [])
        if "pricelist_id" not in fields:
            fields.append("pricelist_id")
        return result

    def _loader_params_product_pricelist(self):
        result = super()._loader_params_product_pricelist()
        channel_pricelist_ids = self._get_sale_channel_pricelist_ids()
        if channel_pricelist_ids:
            result["search_params"]["domain"] = OR(
                [
                    result["search_params"]["domain"],
                    [("id", "in", channel_pricelist_ids)],
                ]
            )
        return result

    def _pos_data_process(self, loaded_data):
        super()._pos_data_process(loaded_data)
        if loaded_data.get("default_pricelist") or not self.config_id.pricelist_id:
            return

        default_pricelist = next(
            (
                pricelist
                for pricelist in loaded_data.get("product.pricelist", [])
                if pricelist["id"] == self.config_id.pricelist_id.id
            ),
            False,
        )
        if default_pricelist:
            loaded_data["default_pricelist"] = default_pricelist

from odoo import models
from odoo.osv.expression import OR


class PosSession(models.Model):
    _inherit = "pos.session"

    def _get_sale_channel_tax_ids(self):
        self.ensure_one()
        channels = self.env["pos.sale.channel"].search(
            [
                ("active", "=", True),
                ("channel_tax_id", "!=", False),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ]
        )
        return channels.mapped("channel_tax_id").ids

    def _loader_params_pos_sale_channel(self):
        result = super()._loader_params_pos_sale_channel()
        fields = result["search_params"].setdefault("fields", [])
        if "channel_tax_id" not in fields:
            fields.append("channel_tax_id")
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        channel_tax_ids = self._get_sale_channel_tax_ids()
        if channel_tax_ids:
            result["search_params"]["domain"] = OR(
                [
                    result["search_params"]["domain"],
                    [("id", "in", channel_tax_ids)],
                ]
            )
        return result

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _pos_ui_models_to_load(self):
        models_to_load = super()._pos_ui_models_to_load()
        models_to_load.append("pos.sale.channel")
        return models_to_load

    def _loader_params_pos_sale_channel(self):
        return {
            "search_params": {
                "domain": [
                    ("active", "=", True),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.company_id.id),
                ],
                "fields": ["name", "sequence", "company_id", "channel_type"],
                "order": "sequence, id",
            }
        }

    def _get_pos_ui_pos_sale_channel(self, params):
        return self.env["pos.sale.channel"].search_read(**params["search_params"])

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        fields = result["search_params"].get("fields")
        # In this POS version, an empty list means "load all fields".
        # Preserve that behavior, otherwise the POS bootstrap loses core fields
        # such as `is_posbox` and fails to initialize.
        if fields:
            for field_name in ["online_checker_channel_ids", "online_checker_can_manage"]:
                if field_name not in fields:
                    fields.append(field_name)
        return result

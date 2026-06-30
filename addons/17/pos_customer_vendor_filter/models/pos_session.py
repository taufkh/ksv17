from odoo import models
from odoo.osv import expression


class PosSession(models.Model):
    _inherit = "pos.session"

    @staticmethod
    def _vendor_only_exclusion_domain():
        return ["|", ("customer_rank", ">", 0), ("supplier_rank", "=", 0)]

    def _internal_user_partner_exclusion_domain(self):
        internal_partner_ids = self.env["res.users"].search(
            [("share", "=", False), ("partner_id", "!=", False)]
        ).mapped("partner_id").ids
        if not internal_partner_ids:
            return []
        return [("id", "not in", internal_partner_ids)]

    def _customer_partner_visibility_domain(self):
        return expression.AND(
            [
                self._vendor_only_exclusion_domain(),
                self._internal_user_partner_exclusion_domain(),
            ]
        )

    def _loader_params_res_partner(self):
        params = super()._loader_params_res_partner()
        existing_domain = params["search_params"].get("domain", [])

        # Keep any existing filters and additionally:
        # 1) exclude vendor-only contacts
        # 2) exclude partners linked to internal users.
        params["search_params"]["domain"] = expression.AND(
            [
                existing_domain,
                self._customer_partner_visibility_domain(),
            ]
        )
        return params

    def _get_pos_ui_res_partner(self, params):
        partner_ids = [res[0] for res in self.config_id.get_limited_partners_loading()]
        search_params = dict(params.get("search_params", {}))
        existing_domain = search_params.get("domain", [])
        search_params["domain"] = expression.AND(
            [
                existing_domain,
                [("id", "in", partner_ids)],
                self._customer_partner_visibility_domain(),
            ]
        )
        return self.env["res.partner"].search_read(**search_params)

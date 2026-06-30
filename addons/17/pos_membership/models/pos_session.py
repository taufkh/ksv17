from odoo import fields, models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_res_partner(self):
        result = super()._loader_params_res_partner()
        if self.company_id.membership_auto_load_members:
            for field_name in [
                "is_custom_member",
                "custom_member_type",
                "custom_member_barcode",
                "total_deposit_balance",
                "total_points",
                "membership_last_checkin_date",
            ]:
                if field_name not in result["search_params"]["fields"]:
                    result["search_params"]["fields"].append(field_name)
        return result

    def _loader_params_res_company(self):
        result = super()._loader_params_res_company()
        for field_name in [
            "membership_barcode_prefix",
            "membership_point_spend_amount",
            "membership_point_value",
            "membership_topup_product_id",
            "membership_deposit_payment_method_id",
            "membership_auto_load_members",
        ]:
            if field_name not in result["search_params"]["fields"]:
                result["search_params"]["fields"].append(field_name)
        return result

    def _loader_params_pos_payment_method(self):
        result = super()._loader_params_pos_payment_method()
        if "is_membership_deposit" not in result["search_params"]["fields"]:
            result["search_params"]["fields"].append("is_membership_deposit")
        return result

    def _loader_params_loyalty_program(self):
        result = super()._loader_params_loyalty_program()
        if "membership_only" not in result["search_params"]["fields"]:
            result["search_params"]["fields"].append("membership_only")
        return result

    def _pos_ui_models_to_load(self):
        result = super()._pos_ui_models_to_load()
        if "daily.free.product.config" not in result:
            result.append("daily.free.product.config")
        return result

    def _loader_params_daily_free_product_config(self):
        return {
            "search_params": {
                "domain": self.env["daily.free.product.config"]._company_active_reward_domain(self.company_id.id),
                "fields": [
                    "date_mode",
                    "date",
                    "date_start",
                    "date_end",
                    "product_id",
                    "reward_product_ids",
                    "reward_product_names",
                    "product_tmpl_id",
                    "active",
                    "company_id",
                ],
            }
        }

    def _get_pos_ui_daily_free_product_config(self, params):
        today = fields.Date.context_today(self)
        reward_config_model = self.env["daily.free.product.config"].sudo()
        rewards = reward_config_model.get_active_rewards_for_day(self.company_id.id, today)
        return rewards.read(params["search_params"]["fields"])

    def resolve_membership_barcode(self, barcode):
        self.ensure_one()
        partner = self.env["res.partner"].sudo().search(
            [
                ("is_custom_member", "=", True),
                ("custom_member_barcode", "=", barcode),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        return partner.get_membership_snapshot() if partner else False

    def get_membership_reward_status(self, partner_id):
        self.ensure_one()
        partner = self.env["res.partner"].browse(partner_id)
        return partner.get_daily_reward_status(company=self.company_id)

from odoo import fields
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosMembership(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.company.membership_point_spend_amount = 10000.0
        cls.company.membership_point_value = 1
        cls.member = cls.env["res.partner"].create(
            {
                "name": "Member Customer",
                "is_custom_member": True,
                "custom_member_type": "paid",
                "customer_rank": 1,
            }
        )

    def test_member_barcode_is_generated(self):
        self.assertTrue(self.member.custom_member_barcode)
        self.assertTrue(self.member.custom_member_barcode.startswith(self.company.membership_barcode_prefix))

    def test_membership_deposit_ledger_updates_balance(self):
        self.member.add_membership_deposit(50000.0, source="adjustment", reference="Initial")
        self.member.invalidate_recordset(["total_deposit_balance"])
        self.assertEqual(self.member.total_deposit_balance, 50000.0)

        self.member.consume_membership_deposit(15000.0, reference="Usage")
        self.member.invalidate_recordset(["total_deposit_balance"])
        self.assertEqual(self.member.total_deposit_balance, 35000.0)

    def test_membership_points_ledger_updates_total(self):
        self.member.add_membership_points(10, reference="Earned")
        self.member.invalidate_recordset(["total_points"])
        self.assertEqual(self.member.total_points, 10)

        self.member.redeem_membership_points(4, reference="Redeemed")
        self.member.invalidate_recordset(["total_points"])
        self.assertEqual(self.member.total_points, 6)

    def test_daily_claim_is_single_use_per_day(self):
        reward_product = self.create_product("Daily Donut", self.categ_anglo, 0.0, standard_price=0.0)
        reward = self.env["daily.free.product.config"].create(
            {
                "date": fields.Date.context_today(self.member),
                "company_id": self.company.id,
                "product_id": reward_product.id,
                "active": True,
            }
        )

        status = self.member.get_daily_reward_status(company=self.company)
        self.assertTrue(status["eligible"])
        self.assertEqual(status["reward_product_id"], reward.product_id.id)

        self.member.consume_daily_reward(reward.product_id)
        status = self.member.get_daily_reward_status(company=self.company)
        self.assertTrue(status["already_claimed"])
        self.assertFalse(status["eligible"])

        with self.assertRaises(UserError):
            self.member.consume_daily_reward(reward.product_id)

    def test_daily_reward_date_range_is_supported(self):
        reward_product = self.create_product("Range Donut", self.categ_anglo, 0.0, standard_price=0.0)
        today = fields.Date.context_today(self.member)
        reward = self.env["daily.free.product.config"].create(
            {
                "date_mode": "date_range",
                "date_start": today,
                "date_end": today,
                "company_id": self.company.id,
                "product_id": reward_product.id,
                "active": True,
            }
        )

        status = self.member.get_daily_reward_status(company=self.company)
        self.assertTrue(status["eligible"])
        self.assertEqual(status["reward_product_id"], reward.product_id.id)

    def test_daily_reward_can_offer_multiple_products(self):
        reward_product_a = self.create_product("Choice Donut A", self.categ_anglo, 0.0, standard_price=0.0)
        reward_product_b = self.create_product("Choice Donut B", self.categ_anglo, 0.0, standard_price=0.0)
        today = fields.Date.context_today(self.member)
        self.env["daily.free.product.config"].create(
            {
                "date": today,
                "company_id": self.company.id,
                "reward_product_ids": [(6, 0, [reward_product_a.id, reward_product_b.id])],
                "active": True,
            }
        )

        status = self.member.get_daily_reward_status(company=self.company)
        self.assertTrue(status["eligible"])
        self.assertEqual(set(status["reward_product_ids"]), {reward_product_a.id, reward_product_b.id})
        self.assertEqual(len(status["reward_products"]), 2)

    def test_daily_reward_overlapping_ranges_are_rejected(self):
        reward_product = self.create_product("Overlap Donut", self.categ_anglo, 0.0, standard_price=0.0)
        today = fields.Date.context_today(self.member)
        self.env["daily.free.product.config"].create(
            {
                "date_mode": "date_range",
                "date_start": today,
                "date_end": today,
                "company_id": self.company.id,
                "product_id": reward_product.id,
                "active": True,
            }
        )

        with self.assertRaises(ValidationError):
            self.env["daily.free.product.config"].create(
                {
                    "date": today,
                    "company_id": self.company.id,
                    "product_id": self.create_product(
                        "Second Overlap Donut", self.categ_anglo, 0.0, standard_price=0.0
                    ).id,
                    "active": True,
                }
            )

    def test_pos_partner_loader_contains_membership_fields(self):
        session = self.open_new_session()
        params = session._loader_params_res_partner()
        for field_name in [
            "is_custom_member",
            "custom_member_type",
            "custom_member_barcode",
            "total_deposit_balance",
            "total_points",
        ]:
            self.assertIn(field_name, params["search_params"]["fields"])

    def test_pos_reward_loader_uses_date_compatibility_fields(self):
        session = self.open_new_session()
        params = session._loader_params_daily_free_product_config()
        self.assertIn("date_mode", params["search_params"]["fields"])
        self.assertIn("date_start", params["search_params"]["fields"])
        self.assertIn("date_end", params["search_params"]["fields"])
        self.assertIn("date", params["search_params"]["fields"])
        self.assertIn("reward_product_ids", params["search_params"]["fields"])
        self.assertIn("reward_product_names", params["search_params"]["fields"])

    def test_loyalty_program_supports_membership_only_flag(self):
        self.assertIn("membership_only", self.env["loyalty.program"]._fields)
        session = self.open_new_session()
        params = session._loader_params_loyalty_program()
        self.assertIn("membership_only", params["search_params"]["fields"])

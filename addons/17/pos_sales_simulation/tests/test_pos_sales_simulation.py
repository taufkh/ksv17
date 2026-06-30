from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosSalesSimulation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["pos.config"].search(
            [("payment_method_ids", "!=", False), ("pricelist_id", "!=", False)],
            limit=1,
        )
        if not cls.config:
            cls.config = cls.env["pos.config"].search([("payment_method_ids", "!=", False)], limit=1)
        if not cls.config:
            raise AssertionError("A POS config with at least one payment method is required for the test.")
        if not cls.config.pricelist_id:
            fallback_pricelist = cls.config.available_pricelist_ids[:1]
            if not fallback_pricelist:
                fallback_pricelist = cls.env["product.pricelist"].create(
                    {
                        "name": "POS Sales Simulation Test Pricelist",
                        "currency_id": cls.config.company_id.currency_id.id,
                    }
                )
            cls.config.write(
                {
                    "available_pricelist_ids": [(4, fallback_pricelist.id)],
                    "pricelist_id": fallback_pricelist.id,
                }
            )
        cls.expected_payment_methods = (
            cls.config.simulation_payment_rule_ids.filtered("active").mapped("payment_method_id")
            or cls.config.payment_method_ids
        )

    def test_form_view_contains_payment_method_override(self):
        view = self.env.ref("pos_sales_simulation.view_pos_sales_simulation_form")

        self.assertIn('name="payment_method_ids"', view.arch_db)
        self.assertIn('string="Allowed Payment Methods"', view.arch_db)

    def test_default_get_prefills_pos_config_and_payment_methods(self):
        defaults = self.env["pos.sales.simulation"].default_get(
            ["pos_config_id", "pos_config_selector", "payment_method_ids", "pricelist_id"]
        )

        self.assertEqual(defaults["pos_config_id"], self.config.id)
        self.assertEqual(defaults["pos_config_selector"], str(self.config.id))
        self.assertEqual(
            set(defaults["payment_method_ids"][0][2]),
            set(self.expected_payment_methods.ids),
        )

    def test_create_applies_payment_methods_from_pos_config(self):
        simulation = self.env["pos.sales.simulation"].create(
            {
                "pos_config_id": self.config.id,
                "pricelist_id": self.config.pricelist_id.id,
                "user_id": self.env.user.id,
                "date_from": fields.Date.today(),
                "date_to": fields.Date.today(),
                "target_revenue": 100.0,
                "transaction_count": 1,
            }
        )

        self.assertEqual(set(simulation.payment_method_ids.ids), set(self.expected_payment_methods.ids))
        self.assertEqual(
            simulation.target_tolerance_pct,
            self.config.simulation_target_tolerance_pct or 5.0,
        )

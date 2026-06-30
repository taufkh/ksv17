from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPosOnlineOrderChecker(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.grab_channel = cls.env["pos.sale.channel"].search([("name", "=", "GrabFood")], limit=1)
        cls.other_channel = cls.env["pos.sale.channel"].search([("name", "=", "Other")], limit=1)
        cls.config.online_checker_channel_ids = [(6, 0, cls.grab_channel.ids)]

        cls.product_a = cls.create_product("Checker Product A", cls.categ_anglo, 25.0, standard_price=8.0)
        cls.product_b = cls.create_product("Checker Product B", cls.categ_anglo, 35.0, standard_price=10.0)

        cls.cashier_user = new_test_user(
            cls.env,
            login="pos_online_checker_cashier",
            groups="point_of_sale.group_pos_user",
            company_id=cls.company.id,
            company_ids=[(6, 0, cls.company.ids)],
        )
        cls.manager_user = new_test_user(
            cls.env,
            login="pos_online_checker_manager",
            groups="point_of_sale.group_pos_user,point_of_sale.group_pos_manager",
            company_id=cls.company.id,
            company_ids=[(6, 0, cls.company.ids)],
        )

    def _create_paid_order(self, product_data, order_channel, line_channels=None):
        session = self.open_new_session()
        order_data = self.create_ui_order_data(product_data)
        order_data["data"]["sale_channel_id"] = order_channel.id
        line_channels = line_channels or {}
        for line in order_data["data"]["lines"]:
            product_id = line[2]["product_id"]
            channel = line_channels.get(product_id)
            if channel:
                line[2]["sale_channel_id"] = channel.id

        result = self.env["pos.order"].create_from_ui([order_data])
        return self.env["pos.order"].browse(result[0]["id"]), session

    def test_non_online_channel_does_not_require_checker(self):
        order, _session = self._create_paid_order([(self.product_a, 2.0)], self.other_channel)

        self.assertFalse(order.online_check_required)
        self.assertEqual(order.online_check_status, "not_required")
        self.assertEqual(order.online_check_total_line_count, 0)

    def test_paid_online_order_starts_pending_then_progress_and_complete(self):
        order, _session = self._create_paid_order([(self.product_a, 2.0)], self.grab_channel)

        self.assertTrue(order.online_check_required)
        self.assertEqual(order.online_check_status, "pending")

        order.save_online_checker_progress(
            {
                "note": "Driver pickup note",
                "line_updates": [{"line_id": order.lines.id, "checked_qty": 1.0}],
            }
        )
        self.assertEqual(order.online_check_status, "in_progress")
        self.assertEqual(order.lines.online_check_qty, 1.0)
        self.assertEqual(order.online_check_note, "Driver pickup note")

        order.complete_online_checker(
            {
                "line_updates": [{"line_id": order.lines.id, "checked_qty": 2.0}],
            }
        )
        self.assertEqual(order.online_check_status, "checked")
        self.assertTrue(order.online_check_completed_at)
        self.assertEqual(order.online_check_completed_by_id, self.env.user)

    def test_non_manager_cannot_override(self):
        order, _session = self._create_paid_order([(self.product_a, 2.0)], self.grab_channel)

        with self.assertRaises(UserError):
            order.with_user(self.cashier_user).override_online_checker(
                "Mismatch accepted",
                {"line_updates": [{"line_id": order.lines.id, "checked_qty": 1.0}]},
            )

    def test_manager_override_requires_reason(self):
        order, _session = self._create_paid_order([(self.product_a, 2.0)], self.grab_channel)

        with self.assertRaises(UserError):
            order.with_user(self.manager_user).override_online_checker(
                "",
                {"line_updates": [{"line_id": order.lines.id, "checked_qty": 1.0}]},
            )

        order.with_user(self.manager_user).override_online_checker(
            "Mismatch approved by manager",
            {"line_updates": [{"line_id": order.lines.id, "checked_qty": 1.0}]},
        )
        self.assertEqual(order.online_check_status, "overridden")
        self.assertEqual(order.online_check_override_by_id, self.manager_user)
        self.assertEqual(order.online_check_override_reason, "Mismatch approved by manager")

    def test_reopen_requires_manager_and_clears_audit(self):
        order, _session = self._create_paid_order([(self.product_a, 2.0)], self.grab_channel)
        order.complete_online_checker(
            {
                "line_updates": [{"line_id": order.lines.id, "checked_qty": 2.0}],
            }
        )

        with self.assertRaises(UserError):
            order.with_user(self.cashier_user).reopen_online_checker()

        order.with_user(self.manager_user).reopen_online_checker()
        self.assertEqual(order.online_check_status, "in_progress")
        self.assertFalse(order.online_check_completed_at)
        self.assertFalse(order.online_check_completed_by_id)
        self.assertEqual(order.lines.online_check_qty, 2.0)

    def test_mixed_channel_only_counts_online_scope_lines(self):
        order, _session = self._create_paid_order(
            [(self.product_a, 2.0), (self.product_b, 1.0)],
            self.grab_channel,
            line_channels={self.product_b.id: self.other_channel},
        )

        self.assertTrue(order.online_check_required)
        self.assertEqual(order.online_check_total_line_count, 1)
        self.assertEqual(order.online_check_ordered_qty_total, 2.0)
        self.assertEqual(order._get_online_checker_lines().product_id, self.product_a)

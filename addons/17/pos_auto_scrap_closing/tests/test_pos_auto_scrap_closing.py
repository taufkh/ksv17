from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.exceptions import UserError
from odoo.tests import new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPosAutoScrapClosing(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.config.auto_scrap_unsold_products = True
        cls.source_location = cls.config.picking_type_id.default_location_src_id

        cls.scrapped_product = cls.create_product(
            "Fresh Brownie",
            cls.categ_anglo,
            35.0,
            standard_price=10.0,
        )
        cls.scrapped_product.product_tmpl_id.auto_scrap_on_pos_closing = True

        cls.regular_product = cls.create_product(
            "Packaged Cookie",
            cls.categ_anglo,
            20.0,
            standard_price=5.0,
        )
        cls.pos_user = new_test_user(
            cls.env,
            login="pos_auto_scrap_user",
            groups="point_of_sale.group_pos_user",
            company_id=cls.company.id,
            company_ids=[(6, 0, cls.company.ids)],
        )

    def _set_inventory(self, product, quantity):
        self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": product.id,
                "inventory_quantity": quantity,
                "location_id": self.source_location.id,
            }
        ).action_apply_inventory()

    def test_close_session_scraps_only_flagged_leftovers(self):
        self._set_inventory(self.scrapped_product, 2.0)
        self._set_inventory(self.regular_product, 3.0)

        session = self.open_new_session()
        session.post_closing_cash_details(0.0)
        result = session.close_session_from_ui()

        scrap = self.env["stock.scrap"].search(
            [
                ("origin", "=", f"{session.name} - POS closing"),
                ("product_id", "=", self.scrapped_product.id),
            ]
        )

        self.assertEqual(result, {"successful": True})
        self.assertEqual(session.state, "closed")
        self.assertEqual(len(scrap), 1)
        self.assertEqual(scrap.state, "done")
        self.assertEqual(scrap.scrap_qty, 2.0)
        self.assertEqual(scrap.pos_session_id, session)
        self.assertEqual(scrap.pos_config_id, session.config_id)
        self.assertTrue(scrap.move_ids.stock_valuation_layer_ids)
        self.assertTrue(scrap.move_ids.account_move_ids)
        self.assertGreater(scrap.loss_value, 0.0)
        self.assertEqual(session.auto_scrap_count, 1)
        self.assertEqual(session.auto_scrap_qty_total, 2.0)
        self.assertGreater(session.auto_scrap_value_total, 0.0)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.scrapped_product, self.source_location, strict=True
            ),
            0.0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                self.regular_product, self.source_location, strict=True
            ),
            3.0,
        )

    def test_preview_wizard_lists_expected_candidates(self):
        self._set_inventory(self.scrapped_product, 2.0)
        self._set_inventory(self.regular_product, 3.0)

        session = self.open_new_session()
        action = session.action_open_auto_scrap_preview()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(action["res_model"], "pos.auto.scrap.preview.wizard")
        self.assertEqual(wizard.session_id, session)
        self.assertEqual(wizard.product_count, 1)
        self.assertEqual(wizard.total_qty, 2.0)
        self.assertEqual(len(wizard.line_ids), 1)
        self.assertEqual(wizard.line_ids.product_id, self.scrapped_product)
        self.assertEqual(wizard.line_ids.scrap_qty, 2.0)
        self.assertGreater(wizard.total_estimated_value, 0.0)
        self.assertFalse(wizard.note)

    def test_preview_projects_leftovers_when_stock_updates_at_closing(self):
        self._set_inventory(self.scrapped_product, 2.0)

        session = self.open_new_session()
        session.update_stock_at_closing = True
        order_data = self.create_ui_order_data([(self.scrapped_product, 1.0)])
        self.env["pos.order"].create_from_ui([order_data])

        action = session.action_open_auto_scrap_preview()
        wizard = self.env[action["res_model"]].browse(action["res_id"])

        self.assertEqual(wizard.product_count, 1)
        self.assertEqual(wizard.total_qty, 1.0)
        self.assertEqual(wizard.line_ids.product_id, self.scrapped_product)
        self.assertEqual(wizard.line_ids.scrap_qty, 1.0)
        self.assertIn("estimasi", wizard.note.lower())

    def test_auto_scrap_threshold_requires_manager(self):
        self._set_inventory(self.scrapped_product, 2.0)
        self.config.write(
            {
                "auto_scrap_require_manager_approval": True,
                "auto_scrap_loss_limit": 5.0,
            }
        )

        session = self.open_new_session()
        session.update_stock_at_closing = True
        order_data = self.create_ui_order_data([(self.scrapped_product, 1.0)])
        self.env["pos.order"].create_from_ui([order_data])

        projected_preview = session.action_open_auto_scrap_preview()
        wizard = self.env[projected_preview["res_model"]].browse(projected_preview["res_id"])
        self.assertIn("manager", wizard.note.lower())

        total_cash = sum(
            session.order_ids.payment_ids.filtered(
                lambda payment: payment.payment_method_id.is_cash_count
            ).mapped("amount")
        )
        session.with_user(self.pos_user).post_closing_cash_details(total_cash)

        ui_result = session.with_user(self.pos_user).close_session_from_ui()
        self.assertEqual(ui_result["successful"], False)
        self.assertEqual(ui_result["redirect"], False)
        self.assertIn("approve", ui_result["message"].lower())
        self.assertEqual(session.state, "opened")

        with self.assertRaises(UserError):
            session.with_user(self.pos_user).action_pos_session_close()

        with self.assertRaises(UserError):
            session.action_pos_session_close()

        approval_action = session.action_open_auto_scrap_approval_wizard()
        approval_wizard = self.env[approval_action["res_model"]].browse(approval_action["res_id"])
        approval_wizard.reason = "Acceptable dessert spoilage for the day"
        self.assertEqual(approval_wizard.action_confirm(), {"type": "ir.actions.act_window_close"})

        self.assertEqual(session.auto_scrap_approval_state, "approved")
        self.assertEqual(session.auto_scrap_approved_by_id, self.env.user)
        self.assertTrue(session.auto_scrap_approved_at)
        self.assertEqual(
            session.auto_scrap_approval_reason,
            "Acceptable dessert spoilage for the day",
        )
        self.assertEqual(session.close_session_from_ui(), {"successful": True})
        self.assertEqual(session.state, "closed")
        self.assertEqual(session.auto_scrap_qty_total, 1.0)

    def test_daily_wastage_report_shows_sold_and_scrapped_quantities(self):
        self._set_inventory(self.scrapped_product, 2.0)

        session = self.open_new_session()
        order_data = self.create_ui_order_data([(self.scrapped_product, 1.0)])
        self.env["pos.order"].create_from_ui([order_data])

        total_cash = sum(
            session.order_ids.payment_ids.filtered(
                lambda payment: payment.payment_method_id.is_cash_count
            ).mapped("amount")
        )
        self.assertEqual(session.post_closing_cash_details(total_cash), {"successful": True})
        self.assertEqual(session.close_session_from_ui(), {"successful": True})
        self.env.flush_all()

        report_lines = self.env["pos.auto.scrap.daily.report"].search(
            [
                ("pos_session_id", "=", session.id),
                ("product_id", "=", self.scrapped_product.id),
            ]
        )

        self.assertTrue(report_lines)
        self.assertIn(session.stop_at.date(), report_lines.mapped("report_date"))
        sold_qty = sum(report_lines.mapped("sold_qty"))
        scrapped_qty = sum(report_lines.mapped("scrapped_qty"))
        loss_value = sum(report_lines.mapped("loss_value"))
        self.assertEqual(sold_qty, 1.0)
        self.assertEqual(scrapped_qty, 1.0)
        self.assertEqual(sold_qty + scrapped_qty, 2.0)
        self.assertGreater(loss_value, 0.0)

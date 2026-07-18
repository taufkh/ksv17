from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosPaymentSafety(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.product = cls.create_product("Payment Safety Product", cls.categ_anglo, 55000.0, standard_price=10.0)

    def _set_payment_commands(self, order_data, amounts):
        payload = order_data.get("data", order_data)
        base_command = payload["statement_ids"][0]
        payment_commands = []
        for amount in amounts:
            payment_values = dict(base_command[2])
            payment_values["amount"] = amount
            payment_commands.append([0, 0, payment_values])
        payload["statement_ids"] = payment_commands
        if "amount_paid" in payload:
            payload["amount_paid"] = sum(amounts)
        if "amount_return" in payload:
            payload["amount_return"] = 0.0
        if "amount_total" in payload:
            payload["amount_total"] = sum(amounts)
        if "amount_tax" in payload and len(payload.get("lines", [])) == 1:
            line_vals = payload["lines"][0][2]
            payload["amount_tax"] = (line_vals.get("price_subtotal_incl") or 0.0) - (
                line_vals.get("price_subtotal") or 0.0
            )
        if payload is not order_data:
            order_data["data"] = payload
        return order_data

    def test_duplicate_payment_lines_same_method_are_collapsed(self):
        self.open_new_session()
        order_data = self.create_ui_order_data([(self.product, 1.0)])
        order_data = self._set_payment_commands(order_data, [33000.0, 22000.0])

        result = self.env["pos.order"].create_from_ui([order_data])
        order = self.env["pos.order"].browse(result[0]["id"])

        self.assertEqual(len(order.payment_ids), 1)
        self.assertEqual(order.payment_ids.payment_method_id, self.config.payment_method_ids[:1])
        self.assertAlmostEqual(order.payment_ids.amount, 55000.0)

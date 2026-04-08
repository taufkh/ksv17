from odoo.tests.common import TransactionCase


class TestPurchaseProductPackagingDefault(TransactionCase):
    def setUp(self):
        super().setUp()
        self.vendor = self.env.ref("base.res_partner_2")
        self.product = self.env["product.product"].create(
            {
                "name": "Test Flour",
                "purchase_ok": True,
                "sale_ok": False,
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            }
        )
        self.pack_small = self.env["product.packaging"].create(
            {
                "name": "PACK",
                "product_id": self.product.id,
                "qty": 12,
                "purchase": True,
                "purchase_is_default": True,
            }
        )
        self.pack_large = self.env["product.packaging"].create(
            {
                "name": "DUS",
                "product_id": self.product.id,
                "qty": 24,
                "purchase": True,
            }
        )
        self.purchase_order = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
            }
        )

    def test_second_default_unsets_first(self):
        self.pack_large.write({"purchase_is_default": True})
        self.pack_small.invalidate_recordset(["purchase_is_default"])
        self.assertFalse(self.pack_small.purchase_is_default)
        self.assertTrue(self.pack_large.purchase_is_default)

    def test_product_change_sets_default_packaging(self):
        line = self.env["purchase.order.line"].new(
            {
                "order_id": self.purchase_order.id,
                "product_id": self.product.id,
            }
        )
        line.onchange_product_id()

        self.assertEqual(line.product_packaging_id, self.pack_small)
        self.assertEqual(line.product_packaging_qty, 1.0)
        self.assertEqual(line.product_qty, 12.0)

    def test_selected_packaging_is_preserved_when_qty_changes(self):
        line = self.env["purchase.order.line"].new(
            {
                "order_id": self.purchase_order.id,
                "product_id": self.product.id,
            }
        )
        line.onchange_product_id()
        line.product_packaging_qty = 2.0
        line._compute_product_qty()
        line._compute_product_packaging_id()

        self.assertEqual(line.product_packaging_id, self.pack_small)
        self.assertEqual(line.product_qty, 24.0)

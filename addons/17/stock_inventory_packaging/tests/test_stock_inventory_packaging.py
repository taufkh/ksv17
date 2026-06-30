from odoo.tests.common import TransactionCase


class TestStockInventoryPackaging(TransactionCase):
    def setUp(self):
        super().setUp()
        self.location = self.env.ref("stock.stock_location_stock")
        self.uom_liter = self.env["uom.uom"].search([("name", "=", "L")], limit=1)
        self.assertTrue(self.uom_liter, "The test database must contain a liter UoM.")
        self.product = self.env["product.product"].create(
            {
                "name": "Inventory Galon",
                "type": "product",
                "uom_id": self.uom_liter.id,
                "uom_po_id": self.uom_liter.id,
            }
        )
        self.packaging = self.env["product.packaging"].create(
            {
                "name": "Galon 19 L",
                "product_id": self.product.id,
                "qty": 19.0,
                "product_uom_id": self.uom_liter.id,
                "inventory_is_default": True,
            }
        )

    def test_second_inventory_default_unsets_first(self):
        second_packaging = self.env["product.packaging"].create(
            {
                "name": "Half Galon 9.5 L",
                "product_id": self.product.id,
                "qty": 9.5,
                "product_uom_id": self.uom_liter.id,
                "inventory_is_default": True,
            }
        )

        self.packaging.invalidate_recordset(["inventory_is_default"])
        self.assertFalse(self.packaging.inventory_is_default)
        self.assertTrue(second_packaging.inventory_is_default)

    def test_product_change_sets_default_inventory_packaging(self):
        quant = self.env["stock.quant"].with_context(inventory_mode=True).new(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
            }
        )

        quant._onchange_product_id_inventory_packaging()

        self.assertEqual(quant.inventory_packaging_id, self.packaging)

    def test_counted_pack_qty_updates_inventory_quantity(self):
        quant = self.env["stock.quant"].with_context(inventory_mode=True).new(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "inventory_packaging_id": self.packaging.id,
            }
        )

        quant.inventory_pack_qty = 3.0

        self.assertEqual(quant.inventory_quantity, 57.0)

    def test_on_hand_pack_qty_is_computed_from_quantity(self):
        self.env["stock.quant"]._update_available_quantity(self.product, self.location, 38.0)
        quant = self.env["stock.quant"]._gather(self.product, self.location, strict=True)
        quant.inventory_packaging_id = self.packaging
        quant._compute_on_hand_pack_qty()

        self.assertEqual(quant.on_hand_pack_qty, 2.0)

    def test_inventory_mode_write_accepts_packaging_fields(self):
        quant = self.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": self.product.id,
                "location_id": self.location.id,
                "inventory_quantity": 19.0,
            }
        )

        quant.with_context(inventory_mode=True).write(
            {
                "inventory_packaging_id": self.packaging.id,
                "inventory_pack_qty": 2.0,
            }
        )

        self.assertEqual(quant.inventory_packaging_id, self.packaging)
        self.assertEqual(quant.inventory_quantity, 38.0)

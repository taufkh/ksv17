import base64
from io import BytesIO

from odoo.tests.common import TransactionCase
from odoo.tools.misc import xlsxwriter


class TestBrownielabStockCountImportWizard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.location = self.env.ref("stock.stock_location_stock")
        self.uom_unit = self.env.ref("uom.product_uom_unit")
        self.product_a = self.env["product.product"].create(
            {
                "name": "Brownie Cup A",
                "default_code": "BL-A",
                "type": "product",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
            }
        )
        self.product_b = self.env["product.product"].create(
            {
                "name": "Brownie Cup B",
                "default_code": "BL-B",
                "type": "product",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
            }
        )
        self.packaging_a = self.env["product.packaging"].create(
            {
                "name": "Pack 25 Pcs",
                "product_id": self.product_a.id,
                "qty": 25.0,
                "product_uom_id": self.uom_unit.id,
                "inventory_is_default": True,
            }
        )
        self.packaging_b = self.env["product.packaging"].create(
            {
                "name": "Pack 25 Pcs",
                "product_id": self.product_b.id,
                "qty": 25.0,
                "product_uom_id": self.uom_unit.id,
                "inventory_is_default": True,
            }
        )

    def _make_xlsx(self, headers, rows):
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Stock Count")
        for col, header in enumerate(headers):
            worksheet.write(0, col, header)
        for row_index, row in enumerate(rows, start=1):
            for col, value in enumerate(row):
                worksheet.write(row_index, col, value)
        workbook.close()
        return base64.b64encode(output.getvalue())

    def _make_wizard(self, **vals):
        defaults = {
            "location_id": self.location.id,
            "upload_filename": "stock_count.xlsx",
        }
        defaults.update(vals)
        return self.env["brownielab.stock.count.import.wizard"].create(defaults)

    def test_import_resolves_same_packaging_name_per_product(self):
        wizard = self._make_wizard(
            upload_file=self._make_xlsx(
                ["default_code", "packaging_name", "counted_pack_qty"],
                [
                    ["BL-A", "Pack 25 Pcs", 2],
                    ["BL-B", "Pack 25 Pcs", 3],
                ],
            )
        )

        wizard.action_import_file()

        quant_a = self.env["stock.quant"].search(
            [("product_id", "=", self.product_a.id), ("location_id", "=", self.location.id)],
            limit=1,
        )
        quant_b = self.env["stock.quant"].search(
            [("product_id", "=", self.product_b.id), ("location_id", "=", self.location.id)],
            limit=1,
        )

        self.assertEqual(quant_a.inventory_packaging_id, self.packaging_a)
        self.assertEqual(quant_b.inventory_packaging_id, self.packaging_b)
        self.assertEqual(quant_a.inventory_quantity, 50.0)
        self.assertEqual(quant_b.inventory_quantity, 75.0)

    def test_import_requires_packaging_when_counted_pack_qty_has_no_default(self):
        self.packaging_a.inventory_is_default = False
        self.env["product.packaging"].create(
            {
                "name": "Pack 10 Pcs",
                "product_id": self.product_a.id,
                "qty": 10.0,
                "product_uom_id": self.uom_unit.id,
            }
        )
        wizard = self._make_wizard(
            upload_file=self._make_xlsx(
                ["default_code", "counted_pack_qty"],
                [["BL-A", 2]],
            )
        )

        with self.assertRaisesRegex(Exception, "Packaging is required"):
            wizard.action_import_file()

    def test_template_contains_products_without_existing_quants(self):
        product_new = self.env["product.product"].create(
            {
                "name": "Brownie New",
                "default_code": "BL-NEW",
                "type": "product",
                "uom_id": self.uom_unit.id,
                "uom_po_id": self.uom_unit.id,
            }
        )
        self.env["product.packaging"].create(
            {
                "name": "Pack 12 Pcs",
                "product_id": product_new.id,
                "qty": 12.0,
                "product_uom_id": self.uom_unit.id,
                "inventory_is_default": True,
            }
        )
        wizard = self._make_wizard()

        rows = wizard._read_excel_rows(wizard._build_template_xlsx())
        rows_by_code = {row["default_code"]: row for row in rows}

        self.assertIn("BL-A", rows_by_code)
        self.assertIn("BL-B", rows_by_code)
        self.assertIn("BL-NEW", rows_by_code)
        self.assertEqual(rows_by_code["BL-A"]["counted_pack_qty"], "")
        self.assertEqual(rows_by_code["BL-NEW"]["counted_pack_qty"], "")

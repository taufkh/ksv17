from odoo import SUPERUSER_ID
from odoo.tests import common


class TestPurchaseVendorMOQ(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.purchase_request_obj = self.env["purchase.request"]
        self.purchase_request_line_obj = self.env["purchase.request.line"]
        self.wiz = self.env["purchase.request.line.make.purchase.order"]
        self.vendor = self.env["res.partner"].create(
            {
                "name": "Vendor MOQ",
                "purchase_moq_qty": 7.0,
                "purchase_moq_note": "1 Carton",
            }
        )
        self.product = self.env["product.product"].create(
            {
                "name": "MOQ Test Product",
                "type": "product",
            }
        )

    def _create_purchase_request_line(self, qty=1.0):
        purchase_request = self.purchase_request_obj.create(
            {
                "picking_type_id": self.env.ref("stock.picking_type_in").id,
                "requested_by": SUPERUSER_ID,
            }
        )
        request_line = self.purchase_request_line_obj.create(
            {
                "request_id": purchase_request.id,
                "product_id": self.product.id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": qty,
            }
        )
        purchase_request.button_approved()
        return request_line

    def test_purchase_request_uses_vendor_moq_qty_fallback(self):
        request_line = self._create_purchase_request_line(qty=1.0)
        wizard = self.wiz.with_context(
            active_model="purchase.request.line",
            active_ids=[request_line.id],
            active_id=request_line.id,
        ).create({"supplier_id": self.vendor.id})

        wizard.make_purchase_order()

        self.assertEqual(request_line.purchase_lines.product_qty, 7.0)

    def test_product_supplierinfo_min_qty_stays_more_specific(self):
        self.env["product.supplierinfo"].create(
            {
                "partner_id": self.vendor.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "min_qty": 10.0,
            }
        )
        request_line = self._create_purchase_request_line(qty=1.0)
        wizard = self.wiz.with_context(
            active_model="purchase.request.line",
            active_ids=[request_line.id],
            active_id=request_line.id,
        ).create({"supplier_id": self.vendor.id})

        wizard.make_purchase_order()

        self.assertEqual(request_line.purchase_lines.product_qty, 10.0)

    def test_manual_purchase_line_suggests_vendor_moq_qty(self):
        purchase = self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
            }
        )
        line = self.env["purchase.order.line"].new(
            {
                "order_id": purchase.id,
                "product_id": self.product.id,
            }
        )

        line.onchange_product_id()

        self.assertEqual(line.product_qty, 7.0)

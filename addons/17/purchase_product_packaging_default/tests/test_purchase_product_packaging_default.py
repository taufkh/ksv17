import base64

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestPurchaseProductPackagingDefault(TransactionCase):
    def setUp(self):
        super().setUp()
        self.purchase_order = self.env["purchase.order"].search([("state", "=", "draft")], limit=1)
        self.confirmed_purchase_order = self.env["purchase.order"].search([("state", "=", "purchase")], limit=1)
        self.assertTrue(self.purchase_order, "The test database must contain at least one draft purchase order.")
        self.assertTrue(
            self.confirmed_purchase_order,
            "The test database must contain at least one confirmed purchase order.",
        )
        self.vendor = self.purchase_order.partner_id
        self.confirmed_vendor = self.confirmed_purchase_order.partner_id
        self.purchase_user_group = self.env.ref("purchase.group_purchase_user")
        self.purchase_manager_group = self.env.ref("purchase.group_purchase_manager")
        self.account_invoice_group = self.env.ref("account.group_account_invoice")
        self.account_manager_group = self.env.ref("account.group_account_manager")
        self.base_user_group = self.env.ref("base.group_user")
        Users = self.env["res.users"].with_context(no_reset_password=True)
        self.request_user = Users.create(
            {
                "name": "Pack Request User",
                "login": "pack_request_user",
                "email": "pack_request_user@example.com",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.base_user_group.id,
                            self.purchase_user_group.id,
                            self.account_invoice_group.id,
                        ],
                    )
                ],
            }
        )
        self.manager_user = Users.create(
            {
                "name": "Pack Manager",
                "login": "pack_manager_user",
                "email": "pack_manager_user@example.com",
                "company_id": self.env.company.id,
                "company_ids": [(6, 0, [self.env.company.id])],
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.base_user_group.id,
                            self.purchase_manager_group.id,
                            self.account_invoice_group.id,
                            self.account_manager_group.id,
                        ],
                    )
                ],
            }
        )
        self.product = self.env["product.product"].search([], limit=1)
        self.assertTrue(self.product, "The test database must contain at least one product variant.")
        self.product.write(
            {
                "name": "Test Flour",
                "purchase_ok": True,
                "sale_ok": False,
                "purchase_method": "purchase",
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
        self.generic_supplierinfo = self.env["product.supplierinfo"].create(
            {
                "partner_id": self.vendor.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_id": self.product.id,
                "price": 15.0,
                "min_qty": 0.0,
            }
        )
        self.pack_small_supplierinfo = self.env["product.supplierinfo"].create(
            {
                "partner_id": self.vendor.id,
                "product_tmpl_id": self.product.product_tmpl_id.id,
                "product_id": self.product.id,
                "product_packaging_id": self.pack_small.id,
                "pack_price": 120.0,
                "min_qty": 0.0,
            }
        )
        if self.confirmed_vendor != self.vendor:
            self.env["product.supplierinfo"].create(
                {
                    "partner_id": self.confirmed_vendor.id,
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "product_id": self.product.id,
                    "price": 15.0,
                    "min_qty": 0.0,
                }
            )
            self.env["product.supplierinfo"].create(
                {
                    "partner_id": self.confirmed_vendor.id,
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "product_id": self.product.id,
                    "product_packaging_id": self.pack_small.id,
                    "pack_price": 120.0,
                    "min_qty": 0.0,
                }
            )
        self.purchase_journal = self.env["account.journal"].search(
            [("type", "=", "purchase"), ("company_id", "=", self.env.company.id)],
            limit=1,
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
        self.assertGreater(line.product_packaging_qty, 0.0)
        self.assertGreater(line.product_qty, 0.0)
        self.assertEqual(line.price_unit, 10.0)
        self.assertEqual(line.pack_price, 120.0)

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

    def test_packaging_change_falls_back_to_generic_supplier_price(self):
        line = self.env["purchase.order.line"].new(
            {
                "order_id": self.purchase_order.id,
                "product_id": self.product.id,
            }
        )
        line.onchange_product_id()
        line.product_packaging_id = self.pack_large
        line._onchange_product_packaging_id()

        self.assertEqual(line.product_packaging_id, self.pack_large)
        self.assertEqual(line.price_unit, 15.0)
        self.assertEqual(line.pack_price, 360.0)

    def test_prepare_account_move_line_carries_pack_fields(self):
        po_line = self.env["purchase.order.line"].create(
            {
                "order_id": self.confirmed_purchase_order.id,
                "product_id": self.product.id,
            }
        )
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.confirmed_purchase_order.partner_id.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
            }
        )

        bill.write({"invoice_line_ids": [Command.create(po_line._prepare_account_move_line(move=bill))]})
        bill_line = bill.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        self.assertEqual(bill_line.product_packaging_id, self.pack_small)
        self.assertGreater(bill_line.product_packaging_qty, 0.0)
        self.assertEqual(bill_line.pack_price, 120.0)
        self.assertEqual(bill_line.purchase_line_id, po_line)

    def test_pack_price_request_notifies_manager_and_blocks_posting(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 12.0,
                            "product_uom_id": self.product.uom_po_id.id,
                            "product_packaging_id": self.pack_small.id,
                            "product_packaging_qty": 1.0,
                            "pack_price": 120.0,
                        }
                    )
                ],
            }
        )
        bill_line = bill.invoice_line_ids.filtered(lambda line: line.display_type == "product")

        bill_line.with_user(self.request_user).write(
            {
                "requested_pack_price": 132.0,
                "pack_price_request_reason": "Vendor invoice changed",
            }
        )
        bill.with_user(self.request_user).action_request_pack_price_approval()

        self.assertEqual(bill_line.pack_price_approval_state, "pending")
        self.assertTrue(
            bill.activity_ids.filtered(
                lambda activity: activity.user_id == self.manager_user
                and activity.summary == "Pack Price Approval"
            )
        )
        with self.assertRaises(UserError):
            bill.action_post()

    def test_manager_can_approve_requested_pack_price(self):
        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "journal_id": self.purchase_journal.id,
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "quantity": 12.0,
                            "product_uom_id": self.product.uom_po_id.id,
                            "product_packaging_id": self.pack_small.id,
                            "product_packaging_qty": 1.0,
                            "pack_price": 120.0,
                        }
                    )
                ],
            }
        )
        bill_line = bill.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        bill_line.with_user(self.request_user).write(
            {
                "requested_pack_price": 144.0,
                "pack_price_request_reason": "Freight included",
            }
        )
        bill.with_user(self.request_user).action_request_pack_price_approval()
        bill.with_user(self.manager_user).action_approve_pack_price_changes()

        self.assertEqual(bill_line.pack_price_approval_state, "approved")
        self.assertEqual(bill_line.pack_price, 144.0)
        self.assertEqual(bill_line.price_unit, 12.0)

    def _make_signature_purchase_order(self):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.vendor.id,
                "currency_id": self.env.company.currency_id.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_qty": 12.0,
                            "product_uom": self.product.uom_po_id.id,
                            "date_planned": fields.Datetime.now(),
                            "product_packaging_id": self.pack_small.id,
                            "product_packaging_qty": 1.0,
                            "pack_price": 120.0,
                            "name": self.product.display_name,
                        }
                    )
                ],
            }
        )

    def test_purchase_order_sign_request_and_manager_approve(self):
        order = self._make_signature_purchase_order()
        request_signature = base64.b64encode(b"requested-signature")
        approve_signature = base64.b64encode(b"approved-signature")

        order.with_user(self.request_user).action_sign_request_approval(request_signature)

        self.assertEqual(order.state, "to approve")
        self.assertEqual(order.approval_signature_state, "pending_approval")
        self.assertEqual(order.requested_by_id, self.request_user)
        self.assertEqual(order.requested_signature, request_signature)
        self.assertTrue(
            order.activity_ids.filtered(
                lambda activity: activity.user_id == self.manager_user
                and activity.summary == "Purchase Order Approval"
            )
        )

        order.with_user(self.manager_user).action_sign_approve_order(approve_signature)

        self.assertEqual(order.state, "purchase")
        self.assertEqual(order.approval_signature_state, "approved")
        self.assertEqual(order.approved_by_id, self.manager_user)
        self.assertEqual(order.approved_signature, approve_signature)

    def test_purchase_order_changes_reset_pending_signature(self):
        order = self._make_signature_purchase_order()
        request_signature = base64.b64encode(b"requested-signature")

        order.with_user(self.request_user).action_sign_request_approval(request_signature)
        order.order_line.filtered(lambda line: line.display_type != "line_section").write({"product_packaging_qty": 2.0})

        self.assertEqual(order.state, "draft")
        self.assertEqual(order.approval_signature_state, "draft")
        self.assertFalse(order.requested_signature)
        self.assertFalse(order.approved_signature)

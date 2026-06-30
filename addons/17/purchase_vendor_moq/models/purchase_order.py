from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    vendor_moq_qty = fields.Float(
        string="Vendor MOQ Qty",
        related="partner_id.commercial_partner_id.purchase_moq_qty",
        readonly=True,
        help="Fallback MOQ applied in the selected product's Purchase UoM.",
    )
    vendor_moq_note = fields.Text(
        string="Vendor MOQ Notes",
        related="partner_id.commercial_partner_id.purchase_moq_note",
        readonly=True,
        help="Reference notes for MOQ rules that cannot be represented as a fixed quantity.",
    )


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _suggest_quantity(self):
        super()._suggest_quantity()
        for line in self:
            if not line.product_id or not line.order_id.partner_id:
                continue
            seller_min_qty = line.product_id.seller_ids.filtered(
                lambda seller: seller.partner_id == line.order_id.partner_id
                and (not seller.product_id or seller.product_id == line.product_id)
            ).sorted(key=lambda seller: seller.min_qty)
            if seller_min_qty:
                continue
            vendor_moq_qty = line.order_id.partner_id.commercial_partner_id.purchase_moq_qty
            if vendor_moq_qty > 0:
                line.product_qty = vendor_moq_qty

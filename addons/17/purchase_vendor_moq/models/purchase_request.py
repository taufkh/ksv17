from odoo import fields, models


class PurchaseRequestLine(models.Model):
    _inherit = "purchase.request.line"

    def _get_supplier_min_qty(self, product, partner_id=False):
        min_qty = super()._get_supplier_min_qty(product, partner_id=partner_id)
        if min_qty or not partner_id:
            return min_qty
        partner = (
            partner_id
            if getattr(partner_id, "_name", None) == "res.partner"
            else self.env["res.partner"].browse(partner_id)
        )
        return partner.commercial_partner_id.purchase_moq_qty or 0.0


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    vendor_moq_qty = fields.Float(
        string="Vendor MOQ Qty",
        related="supplier_id.commercial_partner_id.purchase_moq_qty",
        readonly=True,
        help="Fallback MOQ applied in the selected product's Purchase UoM.",
    )
    vendor_moq_note = fields.Text(
        string="Vendor MOQ Notes",
        related="supplier_id.commercial_partner_id.purchase_moq_note",
        readonly=True,
        help="Reference notes for MOQ rules that cannot be represented as a fixed quantity.",
    )

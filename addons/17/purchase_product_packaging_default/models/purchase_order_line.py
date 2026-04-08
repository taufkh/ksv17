from odoo import api, models
from odoo.tools.float_utils import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _available_purchase_packaging_ids(self):
        self.ensure_one()
        return self.product_id.packaging_ids.filtered(
            lambda packaging: packaging.purchase
            and (
                not packaging.company_id
                or packaging.company_id == self.company_id
            )
        ).sorted(key=lambda packaging: (packaging.sequence, packaging.id))

    def _default_purchase_packaging_id(self):
        self.ensure_one()
        available_packagings = self._available_purchase_packaging_ids()
        default_packaging = available_packagings.filtered("purchase_is_default")[:1]
        if default_packaging:
            return default_packaging
        if len(available_packagings) == 1:
            return available_packagings
        return self.env["product.packaging"]

    def _apply_purchase_packaging(self, packaging, packaging_qty=1.0):
        self.ensure_one()
        if not packaging:
            return
        self.product_uom = self.product_uom or self.product_id.uom_po_id or self.product_id.uom_id
        self.product_packaging_id = packaging
        self.product_packaging_qty = packaging_qty
        self.product_qty = packaging.product_uom_id._compute_quantity(
            packaging.qty * packaging_qty,
            self.product_uom,
        )

    @api.depends("product_id", "product_qty", "product_uom")
    def _compute_product_packaging_id(self):
        for line in self:
            if line.product_packaging_id.product_id != line.product_id:
                line.product_packaging_id = False

            if line.product_packaging_id:
                continue

            if not line.product_id:
                line.product_packaging_id = False
                continue

            default_packaging = line._default_purchase_packaging_id()
            if default_packaging:
                line.product_packaging_id = default_packaging
                continue

            if line.product_qty and line.product_uom:
                line.product_packaging_id = line._available_purchase_packaging_ids()._find_suitable_product_packaging(
                    line.product_qty,
                    line.product_uom,
                )
            else:
                line.product_packaging_id = False

    @api.onchange("product_id")
    def onchange_product_id(self):
        res = super().onchange_product_id()
        for line in self:
            if (
                not line.product_id
                or line.display_type
            ):
                continue
            default_packaging = line._default_purchase_packaging_id()
            if not default_packaging:
                continue

            if line.product_packaging_id and line.product_packaging_id != default_packaging:
                continue

            if not line.product_qty or float_compare(
                line.product_qty,
                1.0,
                precision_rounding=line.product_uom.rounding if line.product_uom else 0.01,
            ) == 0:
                line._apply_purchase_packaging(default_packaging, 1.0)
            elif not line.product_packaging_id:
                line.product_packaging_id = default_packaging
                line._compute_product_packaging_qty()
        return res

    @api.onchange("product_packaging_id")
    def _onchange_product_packaging_id(self):
        res = super()._onchange_product_packaging_id()
        for line in self:
            if line.product_packaging_id and not line.product_qty:
                line._apply_purchase_packaging(line.product_packaging_id, 1.0)
        return res

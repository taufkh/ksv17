from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductSupplierinfo(models.Model):
    _inherit = "product.supplierinfo"

    product_packaging_id = fields.Many2one(
        "product.packaging",
        string="Purchase Pack",
        check_company=True,
    )
    pack_price = fields.Monetary(
        string="Pack Price",
        currency_field="currency_id",
        compute="_compute_pack_price",
        inverse="_inverse_pack_price",
        store=True,
        readonly=False,
    )

    def _get_packaging_qty_in_supplier_uom(self, packaging=None):
        self.ensure_one()
        packaging = packaging or self.product_packaging_id
        if not packaging:
            return 0.0
        return packaging.product_uom_id._compute_quantity(packaging.qty, self.product_uom)

    @api.depends("price", "product_packaging_id", "product_uom")
    def _compute_pack_price(self):
        for seller in self:
            factor = seller._get_packaging_qty_in_supplier_uom()
            seller.pack_price = seller.price * factor if factor else seller.price

    def _inverse_pack_price(self):
        for seller in self:
            factor = seller._get_packaging_qty_in_supplier_uom()
            seller.price = seller.pack_price / factor if factor else seller.pack_price

    @api.constrains("product_packaging_id", "product_id", "product_tmpl_id")
    def _check_product_packaging_id(self):
        for seller in self.filtered("product_packaging_id"):
            packaging = seller.product_packaging_id
            if seller.product_id and packaging.product_id != seller.product_id:
                raise ValidationError(_("The selected purchase pack must belong to the same product variant."))
            if seller.product_tmpl_id and packaging.product_id.product_tmpl_id != seller.product_tmpl_id:
                raise ValidationError(_("The selected purchase pack must belong to the same product template."))

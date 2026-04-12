from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_filtered_sellers(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        sellers = super()._get_filtered_sellers(
            partner_id=partner_id,
            quantity=quantity,
            date=date,
            uom_id=uom_id,
            params=params,
        )
        packaging = (params or {}).get("product_packaging_id")
        if not packaging:
            return sellers
        if isinstance(packaging, int):
            packaging = self.env["product.packaging"].browse(packaging)
        exact_sellers = sellers.filtered(lambda seller: seller.product_packaging_id == packaging)
        if exact_sellers:
            return exact_sellers
        return sellers.filtered(lambda seller: not seller.product_packaging_id)

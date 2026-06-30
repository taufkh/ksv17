from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    purchase_is_default = fields.Boolean(
        string="Default for Purchase",
        help=(
            "If enabled, this packaging is selected automatically on new "
            "purchase order lines for this product."
        ),
    )

    @api.onchange("purchase_is_default")
    def _onchange_purchase_is_default(self):
        for packaging in self:
            if packaging.purchase_is_default:
                packaging.purchase = True

    @api.constrains("purchase_is_default", "purchase", "product_id")
    def _check_purchase_default_configuration(self):
        for packaging in self:
            if packaging.purchase_is_default and not packaging.purchase:
                raise ValidationError(
                    _("A default purchase packaging must also be marked as usable on purchase orders.")
                )

        for packaging in self.filtered("purchase_is_default"):
            others = packaging.product_id.packaging_ids.filtered(
                lambda other: other.id != packaging.id
                and other.purchase
                and other.purchase_is_default
            )
            if others:
                raise ValidationError(
                    _("Only one default purchase packaging is allowed per product.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("purchase_is_default"):
                vals["purchase"] = True
                product_id = vals.get("product_id")
                if product_id:
                    self._unset_other_purchase_defaults(
                        self.env["product.product"].browse(product_id)
                    )
            normalized_vals.append(vals)
        records = super().create(normalized_vals)
        records._sync_purchase_default_flag()
        return records

    def write(self, vals):
        vals = dict(vals)
        if vals.get("purchase_is_default"):
            vals["purchase"] = True
            for packaging in self:
                self._unset_other_purchase_defaults(packaging.product_id, exclude=packaging)
        if vals.get("purchase") is False and "purchase_is_default" not in vals:
            vals["purchase_is_default"] = False
        res = super().write(vals)
        self._sync_purchase_default_flag()
        return res

    def _unset_other_purchase_defaults(self, product, exclude=None):
        if not product:
            return
        others = product.packaging_ids.filtered("purchase_is_default")
        if exclude:
            others -= exclude
        if others:
            others.write({"purchase_is_default": False})

    def _sync_purchase_default_flag(self):
        for packaging in self.filtered(
            lambda pack: pack.purchase and pack.purchase_is_default and pack.product_id
        ):
            self._unset_other_purchase_defaults(packaging.product_id, exclude=packaging)

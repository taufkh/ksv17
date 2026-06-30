from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductPackaging(models.Model):
    _inherit = "product.packaging"

    inventory_is_default = fields.Boolean(
        string="Default for Inventory Count",
        help=(
            "If enabled, this packaging is selected automatically on stock "
            "adjustment lines for this product."
        ),
    )

    @api.constrains("inventory_is_default", "product_id")
    def _check_inventory_default_configuration(self):
        for packaging in self.filtered("inventory_is_default"):
            others = packaging.product_id.packaging_ids.filtered(
                lambda other: other.id != packaging.id and other.inventory_is_default
            )
            if others:
                raise ValidationError(
                    _("Only one default inventory packaging is allowed per product.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        normalized_vals = []
        for vals in vals_list:
            vals = dict(vals)
            if vals.get("inventory_is_default") and vals.get("product_id"):
                self._unset_other_inventory_defaults(
                    self.env["product.product"].browse(vals["product_id"])
                )
            normalized_vals.append(vals)
        records = super().create(normalized_vals)
        records._sync_inventory_default_flag()
        return records

    def write(self, vals):
        vals = dict(vals)
        if vals.get("inventory_is_default"):
            for packaging in self:
                self._unset_other_inventory_defaults(
                    packaging.product_id,
                    exclude=packaging,
                )
        result = super().write(vals)
        self._sync_inventory_default_flag()
        return result

    def _unset_other_inventory_defaults(self, product, exclude=None):
        if not product:
            return
        others = product.packaging_ids.filtered("inventory_is_default")
        if exclude:
            others -= exclude
        if others:
            others.write({"inventory_is_default": False})

    def _sync_inventory_default_flag(self):
        for packaging in self.filtered(lambda pack: pack.inventory_is_default and pack.product_id):
            self._unset_other_inventory_defaults(packaging.product_id, exclude=packaging)

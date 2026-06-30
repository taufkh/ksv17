from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = "stock.quant"

    inventory_packaging_id = fields.Many2one(
        "product.packaging",
        string="Count Pack",
        domain="[('product_id', '=', product_id)]",
    )
    on_hand_pack_qty = fields.Float(
        string="On Hand Pack Qty",
        compute="_compute_on_hand_pack_qty",
        digits="Product Unit of Measure",
    )
    inventory_pack_qty = fields.Float(
        string="Counted Pack Qty",
        compute="_compute_inventory_pack_qty",
        inverse="_inverse_inventory_pack_qty",
        store=True,
        readonly=False,
        digits="Product Unit of Measure",
    )
    inventory_quantity_display = fields.Float(
        string="Converted Quantity",
        compute="_compute_inventory_quantity_display",
        inverse="_inverse_inventory_quantity_display",
        readonly=False,
        digits="Product Unit of Measure",
    )
    inventory_quantity_pack_display = fields.Float(
        string="Converted Quantity",
        compute="_compute_inventory_quantity_pack_display",
        digits="Product Unit of Measure",
    )

    def _get_packaging_qty_in_product_uom(self, packaging=None):
        self.ensure_one()
        packaging = packaging or self.inventory_packaging_id
        if not packaging or not self.product_uom_id:
            return 0.0
        return packaging.product_uom_id._compute_quantity(packaging.qty, self.product_uom_id)

    def _available_inventory_packaging_ids(self):
        self.ensure_one()
        return self.product_id.packaging_ids.sorted(key=lambda packaging: (packaging.sequence, packaging.id))

    def _default_inventory_packaging_id(self):
        self.ensure_one()
        available_packagings = self._available_inventory_packaging_ids()
        default_packaging = available_packagings.filtered("inventory_is_default")[:1]
        if default_packaging:
            return default_packaging
        if "purchase_is_default" in self.env["product.packaging"]._fields:
            purchase_default = available_packagings.filtered("purchase_is_default")[:1]
            if purchase_default:
                return purchase_default
        if len(available_packagings) == 1:
            return available_packagings
        return self.env["product.packaging"]

    @api.depends("quantity", "inventory_packaging_id", "product_uom_id")
    def _compute_on_hand_pack_qty(self):
        for quant in self:
            factor = quant._get_packaging_qty_in_product_uom()
            quant.on_hand_pack_qty = quant.quantity / factor if factor else 0.0

    @api.depends("inventory_quantity", "inventory_packaging_id", "product_uom_id")
    def _compute_inventory_pack_qty(self):
        for quant in self:
            factor = quant._get_packaging_qty_in_product_uom()
            quant.inventory_pack_qty = quant.inventory_quantity / factor if factor else 0.0

    def _inverse_inventory_pack_qty(self):
        for quant in self:
            factor = quant._get_packaging_qty_in_product_uom()
            if factor:
                quant.inventory_quantity = factor * quant.inventory_pack_qty

    @api.depends("inventory_quantity")
    def _compute_inventory_quantity_display(self):
        for quant in self:
            quant.inventory_quantity_display = quant.inventory_quantity

    def _inverse_inventory_quantity_display(self):
        for quant in self:
            quant.inventory_quantity = quant.inventory_quantity_display

    @api.depends("inventory_quantity")
    def _compute_inventory_quantity_pack_display(self):
        for quant in self:
            quant.inventory_quantity_pack_display = quant.inventory_quantity

    @api.onchange("inventory_packaging_id", "inventory_pack_qty")
    def _onchange_inventory_pack_values(self):
        for quant in self.filtered("inventory_packaging_id"):
            quant._inverse_inventory_pack_qty()

    @api.onchange("product_id")
    def _onchange_product_id_inventory_packaging(self):
        for quant in self:
            if quant.inventory_packaging_id.product_id != quant.product_id:
                quant.inventory_packaging_id = False
            if not quant.inventory_packaging_id and quant.product_id:
                quant.inventory_packaging_id = quant._default_inventory_packaging_id()

    @api.constrains("inventory_packaging_id", "product_id")
    def _check_inventory_packaging_product(self):
        for quant in self.filtered("inventory_packaging_id"):
            if quant.inventory_packaging_id.product_id != quant.product_id:
                raise ValidationError(
                    _("The selected count packaging must belong to the same product.")
                )

    @api.model
    def _get_inventory_fields_create(self):
        return super()._get_inventory_fields_create() + [
            "inventory_packaging_id",
            "inventory_pack_qty",
            "inventory_quantity_display",
        ]

    @api.model
    def _get_inventory_fields_write(self):
        return super()._get_inventory_fields_write() + [
            "inventory_packaging_id",
            "inventory_pack_qty",
            "inventory_quantity_display",
        ]

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.with_context(skip_inventory_pack_sync=True).filtered(
            "inventory_packaging_id"
        )._inverse_inventory_pack_qty()
        return records

    def write(self, vals):
        preserved_pack_qty = {}
        if "inventory_quantity" in vals and "inventory_pack_qty" not in vals:
            preserved_pack_qty = {
                quant.id: quant.inventory_pack_qty for quant in self.filtered("inventory_packaging_id")
            }
        result = super().write(vals)
        if self.env.context.get("skip_inventory_pack_sync"):
            return result
        packaged_quants = self.filtered("inventory_packaging_id")
        if preserved_pack_qty:
            for quant in packaged_quants.filtered(lambda record: record.id in preserved_pack_qty):
                quant.with_context(skip_inventory_pack_sync=True).update(
                    {"inventory_pack_qty": preserved_pack_qty[quant.id]}
                )
        elif "inventory_packaging_id" in vals or "inventory_pack_qty" in vals:
            packaged_quants.with_context(skip_inventory_pack_sync=True)._inverse_inventory_pack_qty()
        return result

    def action_set_inventory_quantity(self):
        result = super().action_set_inventory_quantity()
        for quant in self.filtered(lambda record: record.product_id and not record.inventory_packaging_id):
            quant.inventory_packaging_id = quant._default_inventory_packaging_id()
        return result

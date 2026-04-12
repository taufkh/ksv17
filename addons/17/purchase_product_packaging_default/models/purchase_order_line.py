from odoo import api, fields, models
from odoo.tools.float_utils import float_compare


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    pack_price = fields.Monetary(
        string="Pack Price",
        currency_field="currency_id",
        compute="_compute_pack_price",
        inverse="_inverse_pack_price",
        store=True,
        readonly=False,
    )

    def _get_packaging_qty_in_line_uom(self, packaging=None):
        self.ensure_one()
        packaging = packaging or self.product_packaging_id
        uom = self.product_uom or self.product_id.uom_po_id or self.product_id.uom_id
        if not packaging or not uom:
            return 0.0
        return packaging.product_uom_id._compute_quantity(packaging.qty, uom)

    def _get_seller_for_packaging(self):
        self.ensure_one()
        if not self.product_id or not self.partner_id or not self.company_id:
            return self.env["product.supplierinfo"]
        return self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.product_qty,
            date=self.order_id.date_order and self.order_id.date_order.date() or fields.Date.context_today(self),
            uom_id=self.product_uom,
            params=self._get_select_sellers_params(),
        )

    def _get_price_unit_from_seller(self, seller):
        self.ensure_one()
        if not seller:
            return 0.0
        price_unit = self.env["account.tax"]._fix_tax_included_price_company(
            seller.price,
            self.product_id.supplier_taxes_id,
            self.taxes_id,
            self.company_id,
        )
        return seller.currency_id._convert(
            price_unit,
            self.currency_id,
            self.company_id,
            self.date_order or fields.Date.context_today(self),
            False,
        )

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

    @api.depends("price_unit", "product_packaging_id", "product_uom")
    def _compute_pack_price(self):
        for line in self:
            factor = line._get_packaging_qty_in_line_uom()
            line.pack_price = line.price_unit * factor if factor else line.price_unit

    def _inverse_pack_price(self):
        for line in self:
            if line.display_type:
                continue
            factor = line._get_packaging_qty_in_line_uom()
            line.price_unit = line.pack_price / factor if factor else line.pack_price

    @api.depends("product_qty", "product_uom", "company_id", "product_packaging_id")
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()

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
            line._compute_price_unit_and_date_planned_and_name()
        return res

    @api.onchange("product_packaging_id")
    def _onchange_product_packaging_id(self):
        res = super()._onchange_product_packaging_id()
        for line in self:
            if line.product_packaging_id and not line.product_qty:
                line._apply_purchase_packaging(line.product_packaging_id, 1.0)
            if line.product_id and not line.display_type:
                line._compute_price_unit_and_date_planned_and_name()
        return res

    def _get_select_sellers_params(self):
        params = super()._get_select_sellers_params()
        params["product_packaging_id"] = self.product_packaging_id
        return params

    def _prepare_account_move_line(self, move=False):
        res = super()._prepare_account_move_line(move=move)
        if self.display_type:
            return res
        aml_currency = move and move.currency_id or self.currency_id
        date = move and move.date or fields.Date.today()
        res.update(
            {
                "product_packaging_id": self.product_packaging_id.id,
                "product_packaging_qty": self.product_packaging_qty,
                "pack_price": self.currency_id._convert(
                    self.pack_price,
                    aml_currency,
                    self.company_id,
                    date,
                    round=False,
                ),
            }
        )
        return res

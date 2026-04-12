from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    product_packaging_id = fields.Many2one(
        "product.packaging",
        string="Pack",
        domain="[('purchase', '=', True), ('product_id', '=', product_id)]",
        check_company=True,
    )
    product_packaging_qty = fields.Float(
        string="Pack Qty",
        compute="_compute_product_packaging_qty",
        inverse="_inverse_product_packaging_qty",
        store=True,
        readonly=False,
    )
    pack_price = fields.Monetary(
        string="Pack Price",
        currency_field="currency_id",
        compute="_compute_pack_price",
        inverse="_inverse_pack_price",
        store=True,
        readonly=False,
    )
    requested_pack_price = fields.Monetary(
        string="Requested Pack Price",
        currency_field="currency_id",
        copy=False,
    )
    pack_price_request_reason = fields.Text(
        string="Pack Price Request Reason",
        copy=False,
    )
    pack_price_approval_state = fields.Selection(
        [
            ("none", "No Request"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        string="Pack Price Approval",
        default="none",
        copy=False,
        readonly=True,
    )
    pack_price_requested_by_id = fields.Many2one(
        "res.users",
        string="Requested By",
        copy=False,
        readonly=True,
    )
    pack_price_requested_at = fields.Datetime(
        string="Requested At",
        copy=False,
        readonly=True,
    )
    pack_price_approved_by_id = fields.Many2one(
        "res.users",
        string="Approved By",
        copy=False,
        readonly=True,
    )
    pack_price_approved_at = fields.Datetime(
        string="Approved At",
        copy=False,
        readonly=True,
    )

    def _is_purchase_bill_line(self):
        self.ensure_one()
        return self.move_id.move_type == "in_invoice" and self.display_type == "product"

    def _get_packaging_qty_in_line_uom(self, packaging=None):
        self.ensure_one()
        packaging = packaging or self.product_packaging_id
        if not packaging or not self.product_uom_id:
            return 0.0
        return packaging.product_uom_id._compute_quantity(packaging.qty, self.product_uom_id)

    def _get_default_purchase_packaging(self):
        self.ensure_one()
        available_packaging = self.product_id.packaging_ids.filtered(
            lambda packaging: packaging.purchase
            and (not packaging.company_id or packaging.company_id == self.company_id)
        ).sorted(key=lambda packaging: (packaging.sequence, packaging.id))
        default_packaging = available_packaging.filtered("purchase_is_default")[:1]
        if default_packaging:
            return default_packaging
        return available_packaging[:1]

    def _get_bill_seller(self):
        self.ensure_one()
        if not self._is_purchase_bill_line() or not self.product_id or not self.partner_id:
            return self.env["product.supplierinfo"]
        return self.product_id._select_seller(
            partner_id=self.partner_id,
            quantity=self.quantity,
            date=self.move_id.invoice_date or self.move_id.date or fields.Date.context_today(self),
            uom_id=self.product_uom_id,
            params={"product_packaging_id": self.product_packaging_id},
        )

    def _get_price_unit_from_seller(self, seller):
        self.ensure_one()
        if not seller:
            return 0.0
        price_unit = self.env["account.tax"]._fix_tax_included_price_company(
            seller.price,
            self.product_id.supplier_taxes_id,
            self.tax_ids,
            self.company_id,
        )
        return seller.currency_id._convert(
            price_unit,
            self.currency_id,
            self.company_id,
            self.move_id.invoice_date or self.move_id.date or fields.Date.context_today(self),
            False,
        )

    @api.depends("quantity", "product_packaging_id", "product_uom_id")
    def _compute_product_packaging_qty(self):
        for line in self:
            factor = line._get_packaging_qty_in_line_uom()
            line.product_packaging_qty = line.quantity / factor if factor else 0.0

    def _inverse_product_packaging_qty(self):
        for line in self:
            if line.display_type != "product":
                continue
            factor = line._get_packaging_qty_in_line_uom()
            if factor:
                line.quantity = factor * line.product_packaging_qty

    @api.depends("price_unit", "product_packaging_id", "product_uom_id")
    def _compute_pack_price(self):
        for line in self:
            factor = line._get_packaging_qty_in_line_uom()
            line.pack_price = line.price_unit * factor if factor else line.price_unit

    def _inverse_pack_price(self):
        for line in self:
            if line.display_type != "product":
                continue
            factor = line._get_packaging_qty_in_line_uom()
            line.price_unit = line.pack_price / factor if factor else line.pack_price

    @api.depends("product_id", "product_uom_id", "product_packaging_id", "move_id.partner_id")
    def _compute_price_unit(self):
        super()._compute_price_unit()
        for line in self.filtered(
            lambda record: record.move_id.is_purchase_document(include_receipts=True)
            and record.display_type == "product"
            and record.product_id
            and not record.purchase_line_id
        ):
            seller = line._get_bill_seller()
            if seller:
                line.price_unit = line._get_price_unit_from_seller(seller)

    @api.onchange("product_id")
    def _onchange_product_id_packaging(self):
        for line in self:
            if not line._is_purchase_bill_line():
                continue
            if not line.product_packaging_id and line.product_id:
                line.product_packaging_id = line._get_default_purchase_packaging()
            seller = line._get_bill_seller()
            if seller:
                line.price_unit = line._get_price_unit_from_seller(seller)

    @api.onchange("product_packaging_id")
    def _onchange_product_packaging_id(self):
        for line in self:
            if line.display_type != "product":
                continue
            if line.product_packaging_id and not line.quantity:
                factor = line._get_packaging_qty_in_line_uom()
                if factor:
                    line.quantity = factor
                    line.product_packaging_qty = 1.0
            if line._is_purchase_bill_line():
                seller = line._get_bill_seller()
                if seller:
                    line.price_unit = line._get_price_unit_from_seller(seller)

    def write(self, vals):
        if "pack_price" in vals:
            if any(line._is_purchase_bill_line() for line in self) and not (
                self.env.context.get("allow_pack_price_manager_write")
                or self.env.user.has_group("purchase.group_purchase_manager")
                or self.env.user.has_group("account.group_account_manager")
            ):
                raise UserError(
                    _("Only managers can change Pack Price on vendor bills. Submit a pack price request instead.")
                )
        result = super().write(vals)
        if "pack_price" in vals:
            for line in self.filtered(lambda record: record._is_purchase_bill_line()):
                line.move_id.message_post(
                    body=_(
                        "Pack price updated directly by %s for %s.",
                        self.env.user.display_name,
                        line.product_id.display_name,
                    )
                )
        return result

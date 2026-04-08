from odoo import api, fields, models


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    pos_session_id = fields.Many2one(
        "pos.session",
        string="POS Session",
        readonly=True,
        index=True,
        check_company=True,
    )
    pos_config_id = fields.Many2one(
        "pos.config",
        related="pos_session_id.config_id",
        string="Point of Sale",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    loss_value = fields.Monetary(
        string="Loss Value",
        currency_field="currency_id",
        compute="_compute_loss_value",
        store=True,
        readonly=True,
    )

    @api.depends("state", "scrap_qty", "product_id.standard_price", "move_ids.stock_valuation_layer_ids.value")
    def _compute_loss_value(self):
        for scrap in self:
            valuation_values = scrap.move_ids.stock_valuation_layer_ids.mapped("value")
            if valuation_values:
                scrap.loss_value = abs(sum(valuation_values))
                continue

            if scrap.state == "done":
                unit_cost = scrap.product_id.with_company(scrap.company_id).standard_price
                scrap.loss_value = abs(scrap.scrap_qty * unit_cost)
            else:
                scrap.loss_value = 0.0

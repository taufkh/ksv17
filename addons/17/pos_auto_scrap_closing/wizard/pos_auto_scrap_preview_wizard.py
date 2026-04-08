from odoo import api, fields, models


class PosAutoScrapPreviewWizard(models.TransientModel):
    _name = "pos.auto.scrap.preview.wizard"
    _description = "POS Auto Scrap Preview"

    session_id = fields.Many2one("pos.session", required=True, readonly=True)
    note = fields.Text(readonly=True)
    line_ids = fields.One2many(
        "pos.auto.scrap.preview.wizard.line",
        "wizard_id",
        string="Preview Lines",
        readonly=True,
    )
    currency_id = fields.Many2one(related="session_id.auto_scrap_currency_id", readonly=True)
    product_count = fields.Integer(compute="_compute_summary")
    total_qty = fields.Float(compute="_compute_summary")
    total_estimated_value = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_summary",
    )

    @api.depends("line_ids.scrap_qty", "line_ids.estimated_value")
    def _compute_summary(self):
        for wizard in self:
            wizard.product_count = len(wizard.line_ids)
            wizard.total_qty = sum(wizard.line_ids.mapped("scrap_qty"))
            wizard.total_estimated_value = sum(wizard.line_ids.mapped("estimated_value"))


class PosAutoScrapPreviewWizardLine(models.TransientModel):
    _name = "pos.auto.scrap.preview.wizard.line"
    _description = "POS Auto Scrap Preview Line"

    wizard_id = fields.Many2one(
        "pos.auto.scrap.preview.wizard",
        required=True,
        ondelete="cascade",
    )
    product_id = fields.Many2one("product.product", required=True, readonly=True)
    product_uom_id = fields.Many2one("uom.uom", required=True, readonly=True)
    location_id = fields.Many2one("stock.location", readonly=True)
    lot_id = fields.Many2one("stock.lot", readonly=True)
    scrap_qty = fields.Float(readonly=True)
    estimated_value = fields.Monetary(
        currency_field="currency_id",
        readonly=True,
    )
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)

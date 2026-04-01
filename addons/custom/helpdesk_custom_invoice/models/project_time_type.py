from odoo import fields, models


class ProjectTimeType(models.Model):
    _inherit = "project.time.type"

    invoice_product_id = fields.Many2one(
        "product.product",
        string="Invoice Product",
        domain="[('detailed_type', '=', 'service')]",
    )
    invoice_label = fields.Char(
        string="Invoice Label",
        help="Optional label used on invoice lines created from this time type.",
    )

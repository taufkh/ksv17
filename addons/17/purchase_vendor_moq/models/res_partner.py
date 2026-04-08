from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    purchase_moq_qty = fields.Float(
        string="Default MOQ Qty",
        help=(
            "Optional numeric MOQ used as the default minimum quantity when no "
            "product-vendor minimum quantity is configured. This value is "
            "applied in each product's Purchase UoM."
        ),
    )
    purchase_moq_note = fields.Text(
        string="MOQ Notes",
        help=(
            "Vendor ordering notes such as carton requirements, shipping "
            "thresholds, or special MOQ rules. Use product vendor lines when "
            "MOQ differs by product or by unit."
        ),
    )

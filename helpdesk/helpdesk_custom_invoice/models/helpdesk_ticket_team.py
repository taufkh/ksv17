from odoo import fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    allow_billing = fields.Boolean(
        string="Allow Billing",
        default=False,
        help="Allow tickets in this team to create customer invoices from timesheets.",
    )
    default_invoice_product_id = fields.Many2one(
        "product.product",
        string="Default Invoice Product",
        domain="[('detailed_type', '=', 'service')]",
    )
    invoice_grouping = fields.Selection(
        [
            ("time_type", "Group by Time Type"),
            ("timesheet", "One Line per Timesheet"),
            ("single", "Single Consolidated Line"),
        ],
        string="Default Invoice Grouping",
        default="time_type",
    )

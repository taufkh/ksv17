from odoo import fields, models


class HelpdeskSalesHandoff(models.Model):
    _inherit = "helpdesk.sales.handoff"

    source_contract_id = fields.Many2one(
        "helpdesk.support.contract",
        string="Source Contract",
        copy=False,
        tracking=True,
    )

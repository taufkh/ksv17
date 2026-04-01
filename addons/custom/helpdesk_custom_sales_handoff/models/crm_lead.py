from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    sales_handoff_id = fields.Many2one(
        comodel_name="helpdesk.sales.handoff",
        string="Sales Handoff",
        copy=False,
        tracking=True,
    )

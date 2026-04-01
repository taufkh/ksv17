from odoo import api, fields, models


class HelpdeskDispatch(models.Model):
    _inherit = "helpdesk.dispatch"

    support_asset_id = fields.Many2one(
        "helpdesk.support.asset",
        string="Support Asset",
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
    )

    @api.onchange("ticket_id")
    def _onchange_ticket_id_asset(self):
        super()._onchange_ticket_id()
        for dispatch in self:
            if dispatch.ticket_id and dispatch.ticket_id.support_asset_id:
                dispatch.support_asset_id = dispatch.ticket_id.support_asset_id

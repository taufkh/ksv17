from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    support_asset_id = fields.Many2one(
        "helpdesk.support.asset",
        string="Support Asset",
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
    )
    support_asset_state = fields.Selection(
        related="support_asset_id.state",
        string="Asset State",
        store=True,
        readonly=True,
    )
    support_asset_coverage_status = fields.Selection(
        related="support_asset_id.coverage_status",
        string="Asset Coverage",
        store=True,
        readonly=True,
    )

    @api.onchange("partner_id", "support_contract_id")
    def _onchange_support_asset_context(self):
        for ticket in self:
            if not ticket.partner_id:
                ticket.support_asset_id = False
            elif ticket.support_asset_id and ticket.support_asset_id.partner_id != (ticket.commercial_partner_id or ticket.partner_id):
                ticket.support_asset_id = False

    def action_open_support_asset(self):
        self.ensure_one()
        if not self.support_asset_id:
            return False
        return self.support_asset_id.get_formview_action()

    def action_reassign_support_asset(self):
        self.ensure_one()
        partner = self.commercial_partner_id or self.partner_id
        asset = self.env["helpdesk.support.asset"].search(
            [
                ("partner_id", "=", partner.id),
                "|",
                ("support_contract_id", "=", False),
                ("support_contract_id", "=", self.support_contract_id.id),
            ],
            limit=1,
            order="service_level desc, id desc",
        )
        self.support_asset_id = asset.id if asset else False
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Support asset assignment has been refreshed."),
            },
        }

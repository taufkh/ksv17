from odoo import api, fields, models


class HelpdeskSupportContract(models.Model):
    _inherit = "helpdesk.support.contract"

    asset_ids = fields.One2many(
        "helpdesk.support.asset",
        "support_contract_id",
        string="Covered Assets",
    )
    asset_count = fields.Integer(compute="_compute_asset_metrics", store=True)
    active_asset_count = fields.Integer(compute="_compute_asset_metrics", store=True)

    @api.depends("asset_ids", "asset_ids.state")
    def _compute_asset_metrics(self):
        for contract in self:
            contract.asset_count = len(contract.asset_ids)
            contract.active_asset_count = len(
                contract.asset_ids.filtered(lambda asset: asset.state in {"active", "warranty"})
            )

    def action_open_assets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_asset_coverage.action_helpdesk_support_asset"
        )
        action["domain"] = [("support_contract_id", "=", self.id)]
        action["context"] = {
            "default_partner_id": self.partner_id.id,
            "default_support_contract_id": self.id,
        }
        return action

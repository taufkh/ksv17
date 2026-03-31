from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    helpdesk_360_renewal_watch_count = fields.Integer(
        string="Renewal Watches",
        compute="_compute_helpdesk_renewal_360",
        compute_sudo=True,
    )
    helpdesk_360_contract_risk_count = fields.Integer(
        string="Contracts At Risk",
        compute="_compute_helpdesk_renewal_360",
        compute_sudo=True,
    )
    helpdesk_360_renewal_ids = fields.Many2many(
        "helpdesk.contract.renewal",
        string="Customer Renewal Records",
        compute="_compute_helpdesk_renewal_360",
        compute_sudo=True,
    )

    def _compute_helpdesk_renewal_360(self):
        renewal_model = self.env["helpdesk.contract.renewal"].sudo()
        for partner in self:
            root = partner._get_helpdesk_360_root()
            renewals = renewal_model.search(
                [("partner_id", "=", root.id)],
                order="next_follow_up_date asc, id desc",
            )
            risky_states = {"open", "in_review", "handoff_sent"}
            partner.helpdesk_360_renewal_watch_count = len(renewals)
            partner.helpdesk_360_contract_risk_count = len(
                renewals.filtered(lambda renewal: renewal.state in risky_states)
            )
            partner.helpdesk_360_renewal_ids = [(6, 0, renewals.ids)]

    def action_open_helpdesk_360_renewals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_contract_renewal.action_helpdesk_contract_renewal"
        )
        action["domain"] = [("partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

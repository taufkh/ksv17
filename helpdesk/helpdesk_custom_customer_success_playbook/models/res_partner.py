from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    helpdesk_success_playbook_count = fields.Integer(
        string="Success Playbooks",
        compute="_compute_helpdesk_success_playbook_count",
        compute_sudo=True,
    )

    def _compute_helpdesk_success_playbook_count(self):
        model = self.env["helpdesk.customer.success.playbook"].sudo()
        for partner in self:
            root = partner.commercial_partner_id or partner
            partner.helpdesk_success_playbook_count = model.search_count([("partner_id", "=", root.id)])

    def action_open_helpdesk_success_playbooks(self):
        self.ensure_one()
        root = self.commercial_partner_id or self
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_customer_success_playbook.action_helpdesk_customer_success_playbook"
        )
        action["domain"] = [("partner_id", "=", root.id)]
        action["context"] = {"default_partner_id": root.id}
        return action

    def action_create_helpdesk_success_playbook(self):
        self.ensure_one()
        root = self.commercial_partner_id or self
        playbook = self.env["helpdesk.customer.success.playbook"].create(
            {
                "name": _("%(partner)s Success Playbook") % {"partner": root.display_name},
                "partner_id": root.id,
                "owner_id": self.env.user.id,
                "playbook_type": "quarterly_review",
                "health_state": "watch",
                "state": "active",
                "next_action_date": fields.Date.context_today(self),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Customer Success Playbook"),
            "res_model": "helpdesk.customer.success.playbook",
            "view_mode": "form",
            "res_id": playbook.id,
        }

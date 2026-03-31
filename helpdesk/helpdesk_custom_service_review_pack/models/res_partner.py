from odoo import _, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    helpdesk_service_review_pack_count = fields.Integer(
        string="Service Review Packs",
        compute="_compute_helpdesk_service_review_pack_count",
        compute_sudo=True,
    )

    def _compute_helpdesk_service_review_pack_count(self):
        pack_model = self.env["helpdesk.service.review.pack"].sudo()
        for partner in self:
            root = partner.commercial_partner_id or partner
            partner.helpdesk_service_review_pack_count = pack_model.search_count(
                [("partner_id", "=", root.id)]
            )

    def action_generate_helpdesk_service_review_pack(self):
        self.ensure_one()
        partner = self.commercial_partner_id or self
        pack = self.env["helpdesk.service.review.pack"].create(
            {
                "partner_id": partner.id,
                "date_from": fields.Date.start_of(fields.Date.context_today(self), "month"),
                "date_to": fields.Date.context_today(self),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Service Review Pack"),
            "res_model": "helpdesk.service.review.pack",
            "view_mode": "form",
            "res_id": pack.id,
        }

    def action_open_helpdesk_service_review_packs(self):
        self.ensure_one()
        root = self.commercial_partner_id or self
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_service_review_pack.action_helpdesk_service_review_pack"
        )
        action["domain"] = [("partner_id", "=", root.id)]
        action["context"] = {"default_partner_id": root.id}
        return action

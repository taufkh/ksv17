# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # ── Ticket Type portal visibility (helpdesk_type) ─────────────────────────
    helpdesk_mgmt_portal_type = fields.Boolean(
        string="Show Ticket Type in Portal",
        related="company_id.helpdesk_mgmt_portal_type",
        readonly=False,
    )

    # ── Activity Tracking — available models (helpdesk_mgmt_activity) ─────────
    helpdesk_available_model_ids = fields.Many2many(
        "ir.model",
        string="Models Linkable to Tickets",
        help="These models will be selectable as linked records in the ticket activity tracker.",
    )

    def get_values(self):
        res = super().get_values()
        config_param = self.env["ir.config_parameter"].sudo()
        raw = config_param.get_param("helpdesk_mgmt_extended.available_model_ids", "[]")
        try:
            import ast
            ids = ast.literal_eval(raw)
        except Exception:
            ids = []
        res["helpdesk_available_model_ids"] = [(6, 0, ids)]
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "helpdesk_mgmt_extended.available_model_ids",
            str(self.helpdesk_available_model_ids.ids),
        )

# -*- coding: utf-8 -*-
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ── Portal Restriction (helpdesk_portal_restriction) ─────────────────────
    helpdesk_team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_team_partner_rel",
        "partner_id",
        "team_id",
        string="Allowed Helpdesk Teams",
    )
    helpdesk_category_ids = fields.Many2many(
        "helpdesk.ticket.category",
        "helpdesk_category_partner_rel",
        "partner_id",
        "category_id",
        string="Allowed Helpdesk Categories",
    )

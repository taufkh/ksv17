# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTicketCategory(models.Model):
    """Extend helpdesk category with template description and portal restriction."""
    _inherit = "helpdesk.ticket.category"

    # ── Template (helpdesk_mgmt_template) ─────────────────────────────────────
    template_description = fields.Html(
        string="Template Description",
        translate=True,
        help="This content is pre-filled in the ticket description when this category is selected.",
    )

    # ── Portal Restriction (helpdesk_portal_restriction) ─────────────────────
    helpdesk_category_partner_ids = fields.Many2many(
        "res.partner",
        "helpdesk_category_partner_rel",
        "category_id",
        "partner_id",
        string="Allowed Portal Users",
        help="Restrict visibility of this category in the portal to these partners.",
    )

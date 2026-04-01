# -*- coding: utf-8 -*-
from odoo import fields, models


class HelpdeskTicketType(models.Model):
    _name = "helpdesk.ticket.type"
    _description = "Helpdesk Ticket Type"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    team_ids = fields.Many2many(
        "helpdesk.ticket.team",
        "helpdesk_type_team_rel",
        "type_id",
        "team_id",
        string="Teams",
    )
    show_in_portal = fields.Boolean(
        string="Visible in Portal",
        default=True,
        help="When enabled, customers can select this type when submitting tickets via the portal.",
    )

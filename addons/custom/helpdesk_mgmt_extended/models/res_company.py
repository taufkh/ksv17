# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    helpdesk_mgmt_portal_type = fields.Boolean(
        string="Show Ticket Type in Portal",
        default=True,
        help="Allow customers to select the ticket type when submitting via the portal.",
    )

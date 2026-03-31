# -*- coding: utf-8 -*-
from odoo import fields, models, _


class CrmLead(models.Model):
    _inherit = "crm.lead"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Helpdesk Ticket",
        ondelete="set null",
    )

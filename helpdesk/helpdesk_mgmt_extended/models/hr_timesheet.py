# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Helpdesk Ticket",
        ondelete="set null",
        index=True,
    )
    ticket_partner_id = fields.Many2one(
        "res.partner",
        string="Ticket Customer",
        related="ticket_id.partner_id",
        store=True,
    )

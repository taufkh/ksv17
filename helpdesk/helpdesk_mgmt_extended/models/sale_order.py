# -*- coding: utf-8 -*-
from odoo import fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_ticket_sale_order_rel",
        "sale_order_id",
        "ticket_id",
        string="Helpdesk Tickets",
    )
    ticket_count = fields.Integer(
        string="Tickets",
        compute="_compute_ticket_count",
    )

    def _compute_ticket_count(self):
        for order in self:
            order.ticket_count = len(order.ticket_ids)

    def action_open_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [("sale_order_ids", "in", self.id)],
        }

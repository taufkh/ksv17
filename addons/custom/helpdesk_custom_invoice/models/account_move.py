from odoo import _, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_ticket_account_move_rel",
        "move_id",
        "ticket_id",
        string="Helpdesk Tickets",
        copy=False,
    )
    ticket_count = fields.Integer(compute="_compute_ticket_count")

    def _compute_ticket_count(self):
        for move in self:
            move.ticket_count = len(move.ticket_ids)

    def action_open_tickets(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "kanban,tree,form",
            "domain": [("id", "in", self.ticket_ids.ids)],
        }

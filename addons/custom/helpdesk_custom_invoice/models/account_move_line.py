from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    helpdesk_ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Helpdesk Ticket",
        copy=False,
        index=True,
    )
    helpdesk_timesheet_ids = fields.One2many(
        "account.analytic.line",
        "helpdesk_invoice_line_id",
        string="Helpdesk Timesheets",
    )

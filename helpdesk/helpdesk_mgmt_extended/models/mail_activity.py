# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Helpdesk Ticket",
        ondelete="set null",
        index=True,
    )

    def _action_done(self, feedback=False, attachment_ids=None):
        """Override to move the ticket to the next stage when the activity is marked done."""
        tickets_to_advance = self.env["helpdesk.ticket"]
        for activity in self:
            if activity.ticket_id and activity.ticket_id.next_stage_id:
                tickets_to_advance |= activity.ticket_id

        result = super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

        for ticket in tickets_to_advance:
            ticket.sudo().write({"stage_id": ticket.next_stage_id.id})

        return result

# -*- coding: utf-8 -*-
from odoo import models


class MailThread(models.AbstractModel):
    """
    Override _message_route_process to auto-advance ticket stage when a customer
    replies via email.  (helpdesk_ticket_partner_response)
    """
    _inherit = "mail.thread"

    def _message_route_process(self, message, message_dict, routes):
        result = super()._message_route_process(message, message_dict, routes)
        # After routing, check if this is a helpdesk.ticket and the author is the customer
        if self._name == "helpdesk.ticket":
            ticket = self
            team = ticket.team_id
            if (
                team.autoupdate_ticket_stage
                and team.autopupdate_dest_stage_id
                and ticket.stage_id in team.autopupdate_src_stage_ids
            ):
                author_id = message_dict.get("author_id")
                customer_partner = ticket.partner_id
                if author_id and customer_partner and author_id == customer_partner.id:
                    ticket.sudo().write({
                        "stage_id": team.autopupdate_dest_stage_id.id
                    })
        return result

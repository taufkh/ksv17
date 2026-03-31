# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketMerge(models.TransientModel):
    """
    Merge two or more helpdesk tickets into one master ticket.
    (helpdesk_mgmt_merge)
    """
    _name = "helpdesk.ticket.merge"
    _description = "Merge Helpdesk Tickets"

    ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_merge_ticket_rel",
        "wizard_id",
        "ticket_id",
        string="Tickets to Merge",
    )
    master_ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Master Ticket",
        required=True,
        help="All other tickets will be merged into this one.",
    )
    merge_description = fields.Boolean(
        string="Merge Descriptions",
        default=True,
        help="Append the descriptions of the merged tickets to the master ticket.",
    )

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        active_ids = self.env.context.get("active_ids", [])
        if active_ids:
            defaults["ticket_ids"] = [(6, 0, active_ids)]
            defaults["master_ticket_id"] = active_ids[0]
        return defaults

    def merge_tickets(self):
        self.ensure_one()
        tickets_to_merge = self.ticket_ids - self.master_ticket_id
        if not tickets_to_merge:
            raise UserError(_("Please select at least two different tickets to merge."))

        master = self.master_ticket_id

        # Merge descriptions
        if self.merge_description:
            descriptions = [master.description or ""]
            for ticket in tickets_to_merge:
                if ticket.description:
                    descriptions.append(
                        "<p><strong>--- %s ---</strong></p>%s" % (ticket.name, ticket.description)
                    )
            master.description = "".join(descriptions)

        # Merge followers
        self._merge_followers(master, tickets_to_merge)

        # Add a note to master
        self._add_message(
            master,
            _("Merged tickets: %s") % ", ".join(tickets_to_merge.mapped("number")),
        )

        # Close merged tickets and add a note referencing master
        for ticket in tickets_to_merge:
            self._add_message(
                ticket,
                _("This ticket has been merged into %(number)s — %(name)s",
                  number=master.number,
                  name=master.name),
            )
            ticket.closed = True

        return {
            "type": "ir.actions.act_window",
            "name": _("Master Ticket"),
            "res_model": "helpdesk.ticket",
            "res_id": master.id,
            "view_mode": "form",
        }

    def _merge_followers(self, master, tickets):
        all_partners = tickets.mapped("message_partner_ids")
        master.message_subscribe(partner_ids=all_partners.ids)

    def _add_message(self, ticket, body):
        ticket.message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HelpdeskTicketCreateLead(models.TransientModel):
    """
    Wizard to create a CRM lead from a helpdesk ticket.
    (helpdesk_mgmt_crm)
    """
    _name = "helpdesk.ticket.create.lead"
    _description = "Create CRM Lead from Ticket"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        string="Ticket",
        required=True,
    )
    name = fields.Char(string="Opportunity Name", required=True)
    partner_id = fields.Many2one("res.partner", string="Customer")
    team_id = fields.Many2one("crm.team", string="Sales Team")
    user_id = fields.Many2one("res.users", string="Salesperson")
    description = fields.Text(string="Notes")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ticket_id = self.env.context.get("default_ticket_id")
        if ticket_id:
            ticket = self.env["helpdesk.ticket"].browse(ticket_id)
            defaults.update({
                "ticket_id": ticket.id,
                "name": ticket.name,
                "partner_id": ticket.partner_id.id if ticket.partner_id else False,
                "description": ticket.description,
            })
        return defaults

    def action_create_lead(self):
        self.ensure_one()
        lead = self.env["crm.lead"].create({
            "name": self.name,
            "partner_id": self.partner_id.id if self.partner_id else False,
            "team_id": self.team_id.id if self.team_id else False,
            "user_id": self.user_id.id if self.user_id else False,
            "description": self.description,
            "ticket_id": self.ticket_id.id,
        })
        self.ticket_id.message_post(
            body=_("Lead/Opportunity created: <a href='#' data-oe-model='crm.lead' "
                   "data-oe-id='%(id)d'>%(name)s</a>", id=lead.id, name=lead.name),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Lead"),
            "res_model": "crm.lead",
            "res_id": lead.id,
            "view_mode": "form",
        }

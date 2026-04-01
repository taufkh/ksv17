from odoo import fields, models


class HelpdeskCommunicationLog(models.Model):
    _name = "helpdesk.communication.log"
    _description = "Helpdesk Customer Communication Log"
    _order = "logged_at desc, id desc"

    channel_selection = [
        ("portal", "Portal"),
        ("whatsapp", "WhatsApp"),
        ("email", "Email"),
        ("phone", "Phone"),
        ("api", "API"),
        ("manual", "Manual"),
    ]
    direction_selection = [
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    ]
    type_selection = [
        ("customer_update", "Customer Update"),
        ("feedback", "Feedback"),
        ("notification", "Notification"),
        ("follow_up", "Follow-up"),
        ("close_request", "Close Request"),
        ("reopen_request", "Reopen Request"),
        ("status_change", "Status Change"),
    ]
    status_selection = [
        ("done", "Done"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    ticket_id = fields.Many2one("helpdesk.ticket", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one("res.partner", string="Customer Contact")
    company_id = fields.Many2one(related="ticket_id.company_id", store=True, readonly=True)
    team_id = fields.Many2one(related="ticket_id.team_id", store=True, readonly=True)
    user_id = fields.Many2one("res.users", string="Logged By", default=lambda self: self.env.user)
    channel = fields.Selection(selection=channel_selection, required=True, index=True)
    direction = fields.Selection(selection=direction_selection, required=True, index=True)
    communication_type = fields.Selection(selection=type_selection, required=True, index=True)
    status = fields.Selection(selection=status_selection, required=True, default="done", index=True)
    subject = fields.Char(required=True)
    summary = fields.Text()
    body = fields.Text()
    logged_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    source_model = fields.Char()
    source_res_id = fields.Integer()

from odoo import fields, models


class HelpdeskPublicPortalShareWizard(models.TransientModel):
    _name = "helpdesk.public.portal.share.wizard"
    _description = "Helpdesk Public Portal Share Wizard"

    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket", readonly=True)
    public_portal_url = fields.Char(string="Public Portal URL", readonly=True)
    recipient_emails = fields.Char(string="Recipient Emails", readonly=True)
    recipient_phones = fields.Char(string="Recipient Phones", readonly=True)
    email_subject_preview = fields.Char(string="Email Subject Preview", readonly=True)
    email_body_preview = fields.Text(string="Email Body Preview", readonly=True)
    whatsapp_body_preview = fields.Text(string="WhatsApp Message Preview", readonly=True)

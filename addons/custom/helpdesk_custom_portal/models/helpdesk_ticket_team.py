from odoo import fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    portal_share_email_subject_template = fields.Char(
        string="Portal Share Email Subject Template",
        default="[{ticket_number}] Public Ticket Tracking Link",
        help=(
            "Template for email subject when sharing the public portal link. "
            "Available placeholders: {ticket_number}, {ticket_title}, {customer_name}, "
            "{team_name}, {portal_url}, {portal_expiry}"
        ),
    )
    portal_share_email_template = fields.Text(
        string="Portal Share Email Template",
        default=(
            "Hello {customer_name},\n\n"
            "You can track ticket {ticket_number} - {ticket_title} using the secure public link:\n"
            "{portal_url}\n\n"
            "Link validity: {portal_expiry}\n\n"
            "Regards,\n"
            "{team_name}"
        ),
        help=(
            "Template for email body when sharing the public portal link. "
            "Available placeholders: {ticket_number}, {ticket_title}, {customer_name}, "
            "{team_name}, {portal_url}, {portal_expiry}"
        ),
    )
    portal_share_whatsapp_template = fields.Text(
        string="Portal Share WhatsApp Template",
        default=(
            "Hello {customer_name}, this is your support ticket link.\n"
            "Ticket: {ticket_number} - {ticket_title}\n"
            "Track here: {portal_url}\n"
            "Valid until: {portal_expiry}"
        ),
        help=(
            "Template for WhatsApp message when sharing the public portal link. "
            "Available placeholders: {ticket_number}, {ticket_title}, {customer_name}, "
            "{team_name}, {portal_url}, {portal_expiry}"
        ),
    )

    portal_digest_policy = fields.Selection(
        selection=[
            ("ticket", "Use Ticket Preference"),
            ("daily", "Force Daily Digest"),
            ("weekly", "Force Weekly Digest"),
            ("disabled", "Disable Digest"),
        ],
        string="Portal Digest Policy",
        default="ticket",
        help="Control digest frequency policy for all tickets in this team.",
    )
    portal_allow_reopen = fields.Boolean(
        string="Allow Reopen from Portal",
        default=True,
        help="Allow customers to reopen a closed ticket from the portal page.",
    )
    portal_allow_escalation = fields.Boolean(
        string="Allow Escalation Request from Portal",
        default=True,
        help="Allow customers to request urgent escalation from public portal page.",
    )
    portal_escalation_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Portal Escalation Stage",
        domain="[('closed', '=', False)]",
        help="Target stage used when customer requests escalation from portal.",
    )
    portal_reopen_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Portal Reopen Stage",
        domain="[('closed', '=', False)]",
        help="Target stage used when a customer reopens a closed ticket.",
    )

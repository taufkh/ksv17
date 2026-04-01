from odoo import fields, models


class HelpdeskTicketTeam(models.Model):
    _inherit = "helpdesk.ticket.team"

    # ── AI activation ─────────────────────────────────────────────────────────
    ai_enabled = fields.Boolean(
        string="Enable Claude AI",
        default=False,
        help="When enabled, new tickets submitted to this team will be "
             "automatically analysed by Claude.",
    )
    ai_auto_reply = fields.Boolean(
        string="Auto-Post Response to Customer",
        default=False,
        help="For CONFIGURATION_QUERY tickets: automatically post Claude's "
             "answer to the ticket chatter as a public message visible to the "
             "customer via portal.",
    )
    ai_auto_dev_note = fields.Boolean(
        string="Auto-Post Dev Plan as Internal Note",
        default=True,
        help="For BUG_REPORT / FEATURE_REQUEST tickets: automatically post "
             "Claude's development plan as an internal chatter note.",
    )

    # ── Project context ────────────────────────────────────────────────────────
    ai_project_context = fields.Text(
        string="Project Context",
        help="Describe the Odoo project for this team: installed modules, "
             "customisations, tech stack, business domain. Claude uses this "
             "to provide more accurate and relevant answers.\n\n"
             "Example:\n"
             "This is an Odoo 17 Community deployment for a manufacturing "
             "company. Key custom modules: stock_custom_lot_expiry, "
             "mrp_custom_routing. We use OCA helpdesk_mgmt + SLA. "
             "PostgreSQL 15, hosted on Ubuntu 22.04.",
    )
    ai_installed_modules = fields.Text(
        string="Key Installed Modules",
        help="Comma-separated list of the most important installed modules. "
             "Claude uses this to give module-specific guidance.",
    )

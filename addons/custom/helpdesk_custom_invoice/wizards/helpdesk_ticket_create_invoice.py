from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicketCreateInvoiceWizard(models.TransientModel):
    _name = "helpdesk.ticket.create.invoice.wizard"
    _description = "Create Helpdesk Invoice"

    ticket_id = fields.Many2one("helpdesk.ticket", required=True)
    partner_id = fields.Many2one("res.partner", required=True)
    invoice_date = fields.Date(default=fields.Date.context_today, required=True)
    grouping = fields.Selection(
        [
            ("time_type", "Group by Time Type"),
            ("timesheet", "One Line per Timesheet"),
            ("single", "Single Consolidated Line"),
        ],
        required=True,
        default="time_type",
    )
    uninvoiced_hours = fields.Float(compute="_compute_uninvoiced_hours")
    line_count = fields.Integer(compute="_compute_uninvoiced_hours")

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        ticket = self.env["helpdesk.ticket"].browse(defaults.get("ticket_id"))
        if ticket:
            ticket._ensure_billing_feature_enabled()
            defaults.setdefault(
                "partner_id",
                (ticket._get_default_invoice_partner() or self.env["res.partner"]).id,
            )
            defaults.setdefault("grouping", ticket._get_invoice_grouping())
        return defaults

    @api.depends("ticket_id")
    def _compute_uninvoiced_hours(self):
        for wizard in self:
            lines = wizard.ticket_id._get_billable_timesheets(uninvoiced_only=True)
            wizard.line_count = len(lines)
            wizard.uninvoiced_hours = sum(lines.mapped("unit_amount"))

    def action_create_invoice(self):
        self.ensure_one()
        self.ticket_id._ensure_billing_feature_enabled()
        lines = self.ticket_id._get_billable_timesheets(uninvoiced_only=True)
        if not lines:
            raise UserError(_("There are no uninvoiced billable timesheets on this ticket."))
        invoice = self.ticket_id._create_invoice_from_timesheets(
            lines,
            grouping=self.grouping,
            invoice_date=self.invoice_date,
            partner=self.partner_id,
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "res_id": invoice.id,
            "view_mode": "form",
            "target": "current",
        }

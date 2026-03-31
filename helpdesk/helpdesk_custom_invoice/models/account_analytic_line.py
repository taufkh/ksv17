from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    helpdesk_billable = fields.Boolean(
        string="Billable",
        default=True,
        help="When enabled, the line can be invoiced from the linked helpdesk ticket.",
    )
    helpdesk_invoice_line_id = fields.Many2one(
        "account.move.line",
        string="Invoice Line",
        copy=False,
        readonly=True,
        index=True,
    )
    helpdesk_invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        related="helpdesk_invoice_line_id.move_id",
        store=True,
        readonly=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "helpdesk_billable" not in vals:
                time_type = self.env["project.time.type"].browse(vals.get("time_type_id"))
                vals["helpdesk_billable"] = not bool(
                    getattr(time_type, "non_billable", False)
                )
        return super().create(vals_list)

    def write(self, vals):
        if (
            "time_type_id" in vals
            and "helpdesk_billable" not in vals
            and not any(line.helpdesk_invoice_line_id for line in self)
        ):
            time_type = self.env["project.time.type"].browse(vals.get("time_type_id"))
            vals["helpdesk_billable"] = not bool(
                getattr(time_type, "non_billable", False)
            )
        return super().write(vals)

    def unlink(self):
        for line in self:
            if line.helpdesk_invoice_line_id:
                raise ValidationError(
                    _("You cannot delete a timesheet line that is already invoiced.")
                )
        return super().unlink()

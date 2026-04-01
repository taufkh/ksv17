from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    invoice_ids = fields.Many2many(
        "account.move",
        "helpdesk_ticket_account_move_rel",
        "ticket_id",
        "move_id",
        string="Invoices",
        copy=False,
    )
    invoice_count = fields.Integer(compute="_compute_invoice_metrics")
    billable_timesheet_hours = fields.Float(compute="_compute_invoice_metrics")
    uninvoiced_billable_hours = fields.Float(compute="_compute_invoice_metrics")
    invoiced_timesheet_hours = fields.Float(compute="_compute_invoice_metrics")
    invoice_status = fields.Selection(
        [
            ("none", "No Billable Time"),
            ("ready", "Ready to Invoice"),
            ("partial", "Partially Invoiced"),
            ("invoiced", "Fully Invoiced"),
        ],
        compute="_compute_invoice_metrics",
    )

    @api.depends(
        "invoice_ids",
        "timesheet_ids.unit_amount",
        "timesheet_ids.helpdesk_billable",
        "timesheet_ids.helpdesk_invoice_line_id",
    )
    def _compute_invoice_metrics(self):
        for ticket in self:
            billable = ticket.timesheet_ids.filtered(lambda line: line.helpdesk_billable)
            uninvoiced = billable.filtered(lambda line: not line.helpdesk_invoice_line_id)
            invoiced = billable - uninvoiced
            ticket.invoice_count = len(ticket.invoice_ids)
            ticket.billable_timesheet_hours = sum(billable.mapped("unit_amount"))
            ticket.uninvoiced_billable_hours = sum(uninvoiced.mapped("unit_amount"))
            ticket.invoiced_timesheet_hours = sum(invoiced.mapped("unit_amount"))
            if not billable:
                ticket.invoice_status = "none"
            elif uninvoiced and invoiced:
                ticket.invoice_status = "partial"
            elif uninvoiced:
                ticket.invoice_status = "ready"
            else:
                ticket.invoice_status = "invoiced"

    def _get_default_invoice_partner(self):
        self.ensure_one()
        return self.partner_id.commercial_partner_id or self.partner_id

    def _get_billable_timesheets(self, uninvoiced_only=True):
        self.ensure_one()
        lines = self.timesheet_ids.filtered(
            lambda line: line.helpdesk_billable and line.unit_amount > 0
        )
        if uninvoiced_only:
            lines = lines.filtered(lambda line: not line.helpdesk_invoice_line_id)
        return lines.sorted(key=lambda line: (line.date or fields.Date.today(), line.id))

    def _get_invoice_grouping(self):
        self.ensure_one()
        return self.team_id.invoice_grouping or "time_type"

    def _get_sales_journal(self):
        self.ensure_one()
        journal = self.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", self.company_id.id),
            ],
            limit=1,
        )
        if not journal:
            raise UserError(
                _("No sales journal is configured for company %s.", self.company_id.name)
            )
        return journal

    def _get_invoice_product_for_line(self, line):
        self.ensure_one()
        return (
            line.time_type_id.invoice_product_id
            or self.team_id.default_invoice_product_id
        )

    def _get_income_account_for_product(self, product):
        self.ensure_one()
        product = product.with_company(self.company_id)
        account = (
            product.property_account_income_id
            or product.categ_id.property_account_income_categ_id
        )
        if not account:
            raise UserError(
                _("No income account is configured for product %s.", product.display_name)
            )
        return account

    def _prepare_invoice_group_payloads(self, lines, grouping):
        self.ensure_one()
        payloads = []
        grouped = {}
        if grouping == "timesheet":
            for line in lines:
                grouped[(line.id,)] = {
                    "lines": line,
                    "product": self._get_invoice_product_for_line(line),
                    "label": line.name or self.name,
                }
        elif grouping == "single":
            first = lines[:1]
            grouped[("single",)] = {
                "lines": lines,
                "product": self._get_invoice_product_for_line(first) if first else False,
                "label": _("%(ticket)s - Support Services", ticket=self.number),
            }
        else:
            for line in lines:
                key = (
                    self._get_invoice_product_for_line(line).id
                    if self._get_invoice_product_for_line(line)
                    else False,
                    line.time_type_id.id,
                )
                grouped.setdefault(
                    key,
                    {
                        "lines": self.env["account.analytic.line"],
                        "product": self._get_invoice_product_for_line(line),
                        "label": line.time_type_id.invoice_label
                        or line.time_type_id.name
                        or _("Support Services"),
                    },
                )
                grouped[key]["lines"] |= line

        for data in grouped.values():
            lineset = data["lines"]
            product = data["product"]
            if not product:
                missing = ", ".join(lineset.mapped("name"))
                raise UserError(
                    _(
                        "Missing invoice product for one or more billable timesheets: %s",
                        missing,
                    )
                )
            payloads.append(
                {
                    "product": product,
                    "lines": lineset,
                    "name": "%s - %s" % (self.number, data["label"]),
                    "quantity": sum(lineset.mapped("unit_amount")),
                    "price_unit": product.lst_price,
                }
            )
        return payloads

    def _create_invoice_from_timesheets(self, lines, grouping="time_type", invoice_date=False, partner=False):
        self.ensure_one()
        if not self.team_id.allow_billing:
            raise UserError(_("Billing is not enabled for this helpdesk team."))
        if not lines:
            raise UserError(_("There are no billable timesheet lines to invoice."))
        partner = partner or self._get_default_invoice_partner()
        if not partner:
            raise UserError(_("The ticket does not have a customer to invoice."))

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": self._get_sales_journal().id,
                "partner_id": partner.id,
                "invoice_date": invoice_date or fields.Date.context_today(self),
                "invoice_origin": self.number,
                "invoice_user_id": self.user_id.id or False,
                "ticket_ids": [(4, self.id)],
            }
        )

        for payload in self._prepare_invoice_group_payloads(lines, grouping):
            before = invoice.invoice_line_ids
            invoice.write(
                {
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": payload["product"].id,
                                "name": payload["name"],
                                "quantity": payload["quantity"],
                                "price_unit": payload["price_unit"],
                                "account_id": self._get_income_account_for_product(
                                    payload["product"]
                                ).id,
                                "product_uom_id": payload["product"].uom_id.id,
                                "tax_ids": [
                                    (6, 0, payload["product"].taxes_id.filtered(
                                        lambda tax: tax.company_id == invoice.company_id
                                    ).ids)
                                ],
                                "helpdesk_ticket_id": self.id,
                            },
                        )
                    ]
                }
            )
            created_line = invoice.invoice_line_ids - before
            payload["lines"].write({"helpdesk_invoice_line_id": created_line.id})

        self.invoice_ids = [(4, invoice.id)]
        invoice.message_post(
            body=_(
                "Invoice created from helpdesk ticket %(ticket)s (%(title)s).",
                ticket=self.number,
                title=self.name,
            )
        )
        return invoice

    def action_open_create_invoice_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Invoice"),
            "res_model": "helpdesk.ticket.create.invoice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_ticket_id": self.id,
            },
        }

    def action_view_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        action["domain"] = [("ticket_ids", "in", [self.id])]
        action["context"] = {
            "default_move_type": "out_invoice",
            "default_partner_id": self._get_default_invoice_partner().id
            if self._get_default_invoice_partner()
            else False,
            "default_ticket_ids": [(4, self.id)],
        }
        return action

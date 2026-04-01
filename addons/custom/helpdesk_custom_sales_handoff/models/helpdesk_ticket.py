from odoo import _, api, fields, models


SALES_HANDOFF_STATE_SELECTION = [
    ("draft", "Draft"),
    ("requested", "Requested"),
    ("in_review", "In Review"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("converted", "Converted"),
]


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    sales_handoff_ids = fields.One2many(
        comodel_name="helpdesk.sales.handoff",
        inverse_name="ticket_id",
        string="Sales Handoffs",
    )
    sales_handoff_count = fields.Integer(
        compute="_compute_sales_handoff_count",
        string="Sales Handoff Count",
    )
    sales_handoff_state = fields.Selection(
        selection=SALES_HANDOFF_STATE_SELECTION,
        compute="_compute_sales_handoff_state",
        string="Sales Handoff Status",
        store=True,
    )

    @api.depends("sales_handoff_ids")
    def _compute_sales_handoff_count(self):
        grouped = self.env["helpdesk.sales.handoff"].read_group(
            [("ticket_id", "in", self.ids)],
            ["ticket_id"],
            ["ticket_id"],
        )
        counts = {item["ticket_id"][0]: item["ticket_id_count"] for item in grouped}
        for ticket in self:
            ticket.sales_handoff_count = counts.get(ticket.id, 0)

    @api.depends("sales_handoff_ids.state", "sales_handoff_ids.create_date")
    def _compute_sales_handoff_state(self):
        for ticket in self:
            latest = ticket.sales_handoff_ids[:1]
            ticket.sales_handoff_state = latest.state if latest else False

    def action_open_sales_handoffs(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "helpdesk_custom_sales_handoff.action_helpdesk_sales_handoff"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {
            "default_ticket_id": self.id,
            "default_name": _("%(ticket)s - Sales Follow-up")
            % {"ticket": self.number},
            "default_reason": "upsell",
            "default_note": self.description or "",
        }
        return action

    def action_request_sales_handoff(self):
        self.ensure_one()
        form_view = self.env.ref(
            "helpdesk_custom_sales_handoff.view_helpdesk_sales_handoff_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Request Sales Follow-up"),
            "res_model": "helpdesk.sales.handoff",
            "view_mode": "form",
            "views": [(form_view.id, "form")],
            "target": "current",
            "context": {
                "default_ticket_id": self.id,
                "default_name": _("%(ticket)s - Sales Follow-up")
                % {"ticket": self.number},
                "default_reason": "upsell",
                "default_note": self.description or "",
            },
        }

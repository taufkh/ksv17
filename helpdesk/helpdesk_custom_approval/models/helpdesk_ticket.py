from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    approval_ids = fields.One2many(
        comodel_name="helpdesk.ticket.approval",
        inverse_name="ticket_id",
        string="Approvals",
    )
    approval_count = fields.Integer(compute="_compute_approval_metrics", store=True)
    open_approval_count = fields.Integer(compute="_compute_approval_metrics", store=True)
    approval_state = fields.Selection(
        [
            ("none", "No Approval"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("implemented", "Implemented"),
        ],
        compute="_compute_approval_metrics",
        string="Approval Status",
        store=True,
    )

    @api.depends("approval_ids.state")
    def _compute_approval_metrics(self):
        for ticket in self:
            approvals = ticket.approval_ids.sorted(
                key=lambda record: (
                    record.request_date or record.create_date or fields.Datetime.now(),
                    record.id,
                ),
                reverse=True,
            )
            ticket.approval_count = len(approvals)
            ticket.open_approval_count = len(
                approvals.filtered(lambda record: record.state in {"requested", "in_review", "approved"})
            )
            if approvals.filtered(lambda record: record.state in {"requested", "in_review"}):
                ticket.approval_state = "pending"
            elif approvals.filtered(lambda record: record.state == "approved"):
                ticket.approval_state = "approved"
            elif approvals.filtered(lambda record: record.state == "implemented"):
                ticket.approval_state = "implemented"
            elif approvals.filtered(lambda record: record.state == "rejected"):
                ticket.approval_state = "rejected"
            else:
                ticket.approval_state = "none"

    def action_open_approvals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_approval.action_helpdesk_ticket_approval"
        )
        action["domain"] = [("ticket_id", "=", self.id)]
        action["context"] = {
            "default_ticket_id": self.id,
            "default_approver_id": self.team_id.user_id.id or self.user_id.id or self.env.user.id,
        }
        return action

    def action_request_approval(self):
        self.ensure_one()
        form_view = self.env.ref(
            "helpdesk_custom_approval.view_helpdesk_ticket_approval_form"
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Request Approval"),
            "res_model": "helpdesk.ticket.approval",
            "view_mode": "form",
            "views": [(form_view.id, "form")],
            "target": "new",
            "context": {
                "default_ticket_id": self.id,
                "default_approver_id": self.team_id.user_id.id or self.user_id.id or self.env.user.id,
                "default_requester_id": self.env.user.id,
                "default_state": "requested",
            },
        }

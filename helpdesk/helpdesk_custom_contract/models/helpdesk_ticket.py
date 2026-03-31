from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    support_contract_id = fields.Many2one(
        "helpdesk.support.contract",
        string="Support Contract",
        tracking=True,
    )
    support_contract_state = fields.Selection(
        related="support_contract_id.state",
        store=True,
        readonly=True,
        string="Contract State",
    )
    support_contract_sla_tier = fields.Selection(
        related="support_contract_id.sla_tier",
        store=True,
        readonly=True,
        string="Contract SLA Tier",
    )
    contract_coverage_status = fields.Selection(
        [
            ("uncovered", "Uncovered"),
            ("covered", "Covered"),
            ("warning", "Low Balance"),
            ("overrun", "Overrun"),
            ("expired", "Expired"),
            ("suspended", "Suspended"),
        ],
        compute="_compute_contract_status",
        store=True,
        string="Coverage Status",
    )
    contract_remaining_hours = fields.Float(
        compute="_compute_contract_status",
        store=True,
    )

    @api.depends(
        "support_contract_id",
        "support_contract_id.state",
        "support_contract_id.remaining_hours",
        "support_contract_id.warning_hours",
        "support_contract_id.allow_overrun",
    )
    def _compute_contract_status(self):
        for ticket in self:
            contract = ticket.support_contract_id
            ticket.contract_remaining_hours = contract.remaining_hours if contract else 0.0
            if not contract:
                ticket.contract_coverage_status = "uncovered"
            elif contract.state == "expired":
                ticket.contract_coverage_status = "expired"
            elif contract.state == "suspended":
                ticket.contract_coverage_status = "suspended"
            elif contract.included_hours and contract.remaining_hours < 0:
                ticket.contract_coverage_status = "overrun"
            elif (
                contract.included_hours
                and contract.remaining_hours <= contract.warning_hours
            ):
                ticket.contract_coverage_status = "warning"
            else:
                ticket.contract_coverage_status = "covered"

    def _find_applicable_support_contract(self):
        self.ensure_one()
        partner = self.commercial_partner_id or self.partner_id.commercial_partner_id or self.partner_id
        if not partner:
            return self.env["helpdesk.support.contract"]
        domain = [
            ("partner_id", "=", partner.id),
            ("state", "in", ["active", "expiring"]),
        ]
        if self.team_id:
            domain += ["|", ("team_id", "=", False), ("team_id", "=", self.team_id.id)]
        return self.env["helpdesk.support.contract"].search(
            domain,
            order="sla_tier desc, end_date desc, id desc",
            limit=1,
        )

    def _assign_support_contract_if_needed(self, force=False):
        for ticket in self:
            if ticket.support_contract_id and not force:
                continue
            contract = ticket._find_applicable_support_contract()
            ticket.support_contract_id = contract.id if contract else False

    @api.onchange("partner_id", "team_id")
    def _onchange_support_contract_context(self):
        for ticket in self:
            if ticket.partner_id and (not ticket.support_contract_id or not ticket.support_contract_id._matches_ticket(ticket)):
                ticket.support_contract_id = ticket._find_applicable_support_contract()

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets.filtered(lambda ticket: ticket.partner_id and not ticket.support_contract_id)._assign_support_contract_if_needed()
        return tickets

    def write(self, vals):
        result = super().write(vals)
        if {"partner_id", "team_id", "commercial_partner_id"} & set(vals):
            self._assign_support_contract_if_needed(force=not vals.get("support_contract_id"))
        return result

    def action_open_support_contract(self):
        self.ensure_one()
        if not self.support_contract_id:
            return False
        return self.support_contract_id.get_formview_action()

    def action_reassign_support_contract(self):
        self.ensure_one()
        self._assign_support_contract_if_needed(force=True)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Support contract assignment has been refreshed."),
            },
        }


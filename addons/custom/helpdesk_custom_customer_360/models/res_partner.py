from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    helpdesk_360_health = fields.Selection(
        [
            ("quiet", "Quiet"),
            ("stable", "Stable"),
            ("attention", "Needs Attention"),
            ("critical", "Critical"),
        ],
        string="Support Health",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_open_ticket_count = fields.Integer(
        string="Open Tickets",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_closed_ticket_count = fields.Integer(
        string="Closed Tickets",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_overdue_ticket_count = fields.Integer(
        string="SLA Overdue",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_escalated_ticket_count = fields.Integer(
        string="Escalated",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_unassigned_ticket_count = fields.Integer(
        string="Unassigned",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_contract_count = fields.Integer(
        string="Contracts",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_active_contract_count = fields.Integer(
        string="Active Contracts",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_pending_approval_count = fields.Integer(
        string="Pending Approvals",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_dispatch_count = fields.Integer(
        string="Dispatch Count",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_scheduled_dispatch_count = fields.Integer(
        string="Scheduled Dispatches",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_sales_handoff_count = fields.Integer(
        string="Sales Handoff Count",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_knowledge_count = fields.Integer(
        string="Knowledge Article Count",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_portal_view_total = fields.Integer(
        string="Portal Views",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_avg_rating = fields.Float(
        string="Average Rating",
        digits=(16, 2),
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_uninvoiced_hours = fields.Float(
        string="Uninvoiced Hours",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_contract_consumed_hours = fields.Float(
        string="Consumed Contract Hours",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_contract_remaining_hours = fields.Float(
        string="Remaining Contract Hours",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_last_ticket_update = fields.Datetime(
        string="Last Ticket Update",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_last_closed_ticket_date = fields.Datetime(
        string="Last Closed Ticket",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        string="Support Tickets",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_contract_ids = fields.Many2many(
        "helpdesk.support.contract",
        string="Support Contracts",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_approval_ids = fields.Many2many(
        "helpdesk.ticket.approval",
        string="Approvals",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_dispatch_ids = fields.Many2many(
        "helpdesk.dispatch",
        string="Related Dispatches",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_sales_handoff_ids = fields.Many2many(
        "helpdesk.sales.handoff",
        string="Related Sales Handoffs",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_invoice_ids = fields.Many2many(
        "account.move",
        string="Related Invoices",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )
    helpdesk_360_knowledge_ids = fields.Many2many(
        "document.page",
        string="Related Knowledge Articles",
        compute="_compute_helpdesk_360",
        compute_sudo=True,
    )

    def _get_helpdesk_360_root(self):
        self.ensure_one()
        return self.commercial_partner_id or self

    def _get_helpdesk_360_tickets(self):
        self.ensure_one()
        root = self._get_helpdesk_360_root()
        return self.env["helpdesk.ticket"].sudo().search(
            [("commercial_partner_id", "=", root.id)],
            order="create_date desc, id desc",
        )

    def _compute_helpdesk_360(self):
        contract_model = self.env["helpdesk.support.contract"].sudo()
        approval_model = self.env["helpdesk.ticket.approval"].sudo()
        dispatch_model = self.env["helpdesk.dispatch"].sudo()
        handoff_model = self.env["helpdesk.sales.handoff"].sudo()
        page_model = self.env["document.page"].sudo()

        for partner in self:
            root = partner._get_helpdesk_360_root()
            tickets = partner._get_helpdesk_360_tickets()
            contracts = contract_model.search(
                [("partner_id", "=", root.id)],
                order="end_date desc, id desc",
            )
            approvals = approval_model.search(
                [("ticket_id", "in", tickets.ids)],
                order="request_date desc, id desc",
            )
            dispatches = dispatch_model.search(
                [("ticket_id", "in", tickets.ids)],
                order="scheduled_start desc, id desc",
            )
            handoffs = handoff_model.search(
                [("ticket_id", "in", tickets.ids)],
                order="request_date desc, id desc",
            )
            invoices = tickets.mapped("invoice_ids").sorted(
                key=lambda move: (move.invoice_date or fields.Date.today(), move.id),
                reverse=True,
            )
            knowledge = page_model.search(
                [("helpdesk_ticket_ids", "in", tickets.ids), ("is_helpdesk_article", "=", True)],
                order="write_date desc, id desc",
            )
            ratings = tickets.mapped("rating_ids").filtered(
                lambda rating: rating.consumed and rating.rating
            )

            open_tickets = tickets.filtered(lambda ticket: not ticket.closed)
            overdue_tickets = open_tickets.filtered("sla_expired")
            escalated_tickets = tickets.filtered("escalated")
            unassigned_tickets = open_tickets.filtered(lambda ticket: not ticket.user_id)
            active_contracts = contracts.filtered(
                lambda contract: contract.state in {"active", "expiring"}
            )
            pending_approvals = approvals.filtered(
                lambda approval: approval.state in {"requested", "in_review", "approved"}
            )
            scheduled_dispatches = dispatches.filtered(
                lambda dispatch: dispatch.state in {"scheduled", "en_route", "on_site"}
            )
            avg_rating = (
                sum(ratings.mapped("rating")) / len(ratings)
                if ratings
                else 0.0
            )

            if overdue_tickets or escalated_tickets:
                health = "critical"
            elif pending_approvals or scheduled_dispatches or unassigned_tickets:
                health = "attention"
            elif tickets or active_contracts:
                health = "stable"
            else:
                health = "quiet"

            partner.helpdesk_360_health = health
            partner.helpdesk_360_open_ticket_count = len(open_tickets)
            partner.helpdesk_360_closed_ticket_count = len(tickets) - len(open_tickets)
            partner.helpdesk_360_overdue_ticket_count = len(overdue_tickets)
            partner.helpdesk_360_escalated_ticket_count = len(escalated_tickets)
            partner.helpdesk_360_unassigned_ticket_count = len(unassigned_tickets)
            partner.helpdesk_360_contract_count = len(contracts)
            partner.helpdesk_360_active_contract_count = len(active_contracts)
            partner.helpdesk_360_pending_approval_count = len(pending_approvals)
            partner.helpdesk_360_dispatch_count = len(dispatches)
            partner.helpdesk_360_scheduled_dispatch_count = len(scheduled_dispatches)
            partner.helpdesk_360_sales_handoff_count = len(handoffs)
            partner.helpdesk_360_invoice_count = len(invoices)
            partner.helpdesk_360_knowledge_count = len(knowledge)
            partner.helpdesk_360_portal_view_total = sum(
                tickets.mapped("public_portal_view_count")
            )
            partner.helpdesk_360_avg_rating = avg_rating
            partner.helpdesk_360_uninvoiced_hours = sum(
                tickets.mapped("uninvoiced_billable_hours")
            )
            partner.helpdesk_360_contract_consumed_hours = sum(
                active_contracts.mapped("consumed_hours")
            )
            partner.helpdesk_360_contract_remaining_hours = sum(
                active_contracts.mapped("remaining_hours")
            )
            partner.helpdesk_360_last_ticket_update = max(
                tickets.mapped("write_date"),
                default=False,
            )
            partner.helpdesk_360_last_closed_ticket_date = max(
                tickets.filtered("closed_date").mapped("closed_date"),
                default=False,
            )
            partner.helpdesk_360_ticket_ids = [(6, 0, tickets.ids)]
            partner.helpdesk_360_contract_ids = [(6, 0, contracts.ids)]
            partner.helpdesk_360_approval_ids = [(6, 0, approvals.ids)]
            partner.helpdesk_360_dispatch_ids = [(6, 0, dispatches.ids)]
            partner.helpdesk_360_sales_handoff_ids = [(6, 0, handoffs.ids)]
            partner.helpdesk_360_invoice_ids = [(6, 0, invoices.ids)]
            partner.helpdesk_360_knowledge_ids = [(6, 0, knowledge.ids)]

    def action_open_helpdesk_360_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_mgmt.helpdesk_ticket_action"
        )
        action["domain"] = [("commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        action["context"] = {"search_default_open": 0}
        return action

    def action_open_helpdesk_360_contracts(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_contract.action_helpdesk_support_contract"
        )
        action["domain"] = [("partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

    def action_open_helpdesk_360_approvals(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_approval.action_helpdesk_ticket_approval"
        )
        action["domain"] = [("ticket_id.commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

    def action_open_helpdesk_360_dispatches(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_dispatch.action_helpdesk_dispatch"
        )
        action["domain"] = [("ticket_id.commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

    def action_open_helpdesk_360_sales_handoffs(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_sales_handoff.action_helpdesk_sales_handoff"
        )
        action["domain"] = [("ticket_id.commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

    def action_open_helpdesk_360_invoices(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        action["domain"] = [("ticket_ids.commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

    def action_open_helpdesk_360_knowledge(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_knowledge.action_helpdesk_knowledge_articles"
        )
        action["domain"] = [("helpdesk_ticket_ids.commercial_partner_id", "=", self._get_helpdesk_360_root().id)]
        return action

from odoo import _, api, fields, models


class HelpdeskSupportAsset(models.Model):
    _name = "helpdesk.support.asset"
    _description = "Helpdesk Support Asset"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "partner_id, site_name, name"

    asset_type_selection = [
        ("site", "Site"),
        ("device", "Device"),
        ("business_process", "Business Process"),
        ("portal_access", "Portal Access"),
        ("application", "Application"),
    ]
    state_selection = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("warranty", "Warranty"),
        ("retired", "Retired"),
    ]
    coverage_status_selection = [
        ("covered", "Covered"),
        ("warning", "Low Balance"),
        ("expired", "Expired"),
        ("suspended", "Suspended"),
        ("uncovered", "Uncovered"),
    ]
    service_level_selection = [
        ("standard", "Standard"),
        ("premium", "Premium"),
        ("critical", "Critical"),
    ]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
        domain=[("is_company", "=", True)],
        tracking=True,
    )
    company_id = fields.Many2one(related="partner_id.company_id", store=True, readonly=True)
    support_contract_id = fields.Many2one(
        "helpdesk.support.contract",
        string="Support Contract",
        tracking=True,
        domain="[('partner_id', '=', partner_id)]",
    )
    team_id = fields.Many2one(
        related="support_contract_id.team_id",
        store=True,
        readonly=True,
    )
    asset_type = fields.Selection(
        selection=asset_type_selection,
        required=True,
        default="site",
        tracking=True,
    )
    state = fields.Selection(
        selection=state_selection,
        required=True,
        default="active",
        tracking=True,
    )
    coverage_status = fields.Selection(
        selection=coverage_status_selection,
        compute="_compute_coverage",
        store=True,
    )
    service_level = fields.Selection(
        selection=service_level_selection,
        default="standard",
        tracking=True,
    )
    site_name = fields.Char(tracking=True)
    reference_code = fields.Char(tracking=True)
    serial_number = fields.Char(tracking=True)
    location = fields.Char(tracking=True)
    notes = fields.Html()
    ticket_ids = fields.One2many(
        "helpdesk.ticket",
        "support_asset_id",
        string="Tickets",
    )
    dispatch_ids = fields.One2many(
        "helpdesk.dispatch",
        "support_asset_id",
        string="Dispatches",
    )
    ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    open_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    overdue_ticket_count = fields.Integer(compute="_compute_metrics", store=True)
    dispatch_count = fields.Integer(compute="_compute_metrics", store=True)
    active_dispatch_count = fields.Integer(compute="_compute_metrics", store=True)
    last_ticket_update = fields.Datetime(compute="_compute_metrics", store=True)

    @api.depends(
        "support_contract_id",
        "support_contract_id.state",
        "support_contract_id.remaining_hours",
        "support_contract_id.warning_hours",
    )
    def _compute_coverage(self):
        for asset in self:
            contract = asset.support_contract_id
            if not contract:
                asset.coverage_status = "uncovered"
            elif contract.state == "expired":
                asset.coverage_status = "expired"
            elif contract.state == "suspended":
                asset.coverage_status = "suspended"
            elif contract.included_hours and contract.remaining_hours <= contract.warning_hours:
                asset.coverage_status = "warning"
            else:
                asset.coverage_status = "covered"

    @api.depends(
        "ticket_ids",
        "ticket_ids.closed",
        "ticket_ids.sla_deadline",
        "ticket_ids.write_date",
        "dispatch_ids",
        "dispatch_ids.state",
    )
    def _compute_metrics(self):
        now = fields.Datetime.now()
        for asset in self:
            tickets = asset.ticket_ids
            dispatches = asset.dispatch_ids
            asset.ticket_count = len(tickets)
            asset.open_ticket_count = len(tickets.filtered(lambda ticket: not ticket.closed))
            asset.overdue_ticket_count = len(
                tickets.filtered(
                    lambda ticket: not ticket.closed
                    and ticket.sla_deadline
                    and ticket.sla_deadline < now
                )
            )
            asset.dispatch_count = len(dispatches)
            asset.active_dispatch_count = len(
                dispatches.filtered(lambda dispatch: dispatch.state in {"draft", "scheduled", "en_route", "on_site"})
            )
            asset.last_ticket_update = max(tickets.mapped("write_date")) if tickets else False

    def action_open_tickets(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_mgmt.helpdesk_ticket_action")
        action["domain"] = [("support_asset_id", "=", self.id)]
        action["context"] = {"search_default_open": 0}
        return action

    def action_open_dispatches(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk_custom_dispatch.action_helpdesk_dispatch")
        action["domain"] = [("support_asset_id", "=", self.id)]
        return action

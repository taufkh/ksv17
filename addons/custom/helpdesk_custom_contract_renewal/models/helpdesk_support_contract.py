from odoo import api, fields, models


class HelpdeskSupportContract(models.Model):
    _inherit = "helpdesk.support.contract"

    renewal_watch_ids = fields.One2many(
        "helpdesk.contract.renewal",
        "contract_id",
        string="Renewal Watches",
    )
    renewal_watch_count = fields.Integer(
        compute="_compute_renewal_metrics",
        store=True,
    )
    renewal_open_watch_count = fields.Integer(
        compute="_compute_renewal_metrics",
        store=True,
    )
    low_hours_alert = fields.Boolean(
        compute="_compute_renewal_metrics",
        store=True,
    )
    expiry_alert = fields.Boolean(
        compute="_compute_renewal_metrics",
        store=True,
    )
    renewal_status = fields.Selection(
        [
            ("none", "None"),
            ("open", "Open"),
            ("in_review", "In Review"),
            ("handoff_sent", "Handoff Sent"),
            ("won", "Won"),
            ("lost", "Lost"),
            ("dismissed", "Dismissed"),
        ],
        compute="_compute_renewal_metrics",
        store=True,
    )

    @api.depends(
        "renewal_watch_ids.state",
        "renewal_watch_ids.create_date",
        "end_date",
        "remaining_hours",
        "warning_hours",
        "included_hours",
        "state",
    )
    def _compute_renewal_metrics(self):
        today = fields.Date.today()
        for contract in self:
            watches = contract.renewal_watch_ids.sorted(
                key=lambda renewal: (
                    renewal.next_follow_up_date or fields.Date.today(),
                    renewal.id,
                ),
                reverse=True,
            )
            open_watches = watches.filtered(
                lambda renewal: renewal.state in {"open", "in_review", "handoff_sent"}
            )
            days_to_expiry = 9999
            if contract.end_date:
                days_to_expiry = (contract.end_date - today).days
            contract.renewal_watch_count = len(watches)
            contract.renewal_open_watch_count = len(open_watches)
            contract.low_hours_alert = bool(
                contract.included_hours
                and contract.state in {"active", "expiring"}
                and contract.remaining_hours <= contract.warning_hours
            )
            contract.expiry_alert = (
                contract.state in {"active", "expiring"} and days_to_expiry <= 14
            )
            contract.renewal_status = open_watches[:1].state if open_watches else (
                watches[:1].state if watches else "none"
            )

    def _get_latest_support_ticket(self):
        self.ensure_one()
        return self.ticket_ids.sorted(
            key=lambda ticket: (ticket.write_date or ticket.create_date or fields.Datetime.now(), ticket.id),
            reverse=True,
        )[:1]

    def action_open_renewal_watchlist(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "helpdesk_custom_contract_renewal.action_helpdesk_contract_renewal"
        )
        action["domain"] = [("contract_id", "=", self.id)]
        return action

    def action_create_renewal_watch(self):
        self.ensure_one()
        open_watch = self.renewal_watch_ids.filtered(
            lambda renewal: renewal.state in {"open", "in_review", "handoff_sent"}
        )[:1]
        if open_watch:
            return open_watch.get_formview_action()
        renewal = self.env["helpdesk.contract.renewal"].create(
            self.env["helpdesk.contract.renewal"]._prepare_watch_vals(
                self,
                auto_generated=False,
            )
        )
        return renewal.get_formview_action()

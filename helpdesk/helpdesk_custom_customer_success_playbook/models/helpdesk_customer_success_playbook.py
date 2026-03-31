from odoo import _, api, fields, models


class HelpdeskCustomerSuccessPlaybook(models.Model):
    _name = "helpdesk.customer.success.playbook"
    _description = "Helpdesk Customer Success Playbook"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "next_action_date asc, id desc"

    playbook_type_selection = [
        ("quarterly_review", "Quarterly Review"),
        ("adoption_check", "Adoption Check"),
        ("renewal_readiness", "Renewal Readiness"),
        ("risk_recovery", "Risk Recovery"),
    ]
    health_state_selection = [
        ("on_track", "On Track"),
        ("watch", "Watch"),
        ("at_risk", "At Risk"),
    ]
    cadence_selection = [
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("custom", "Custom"),
    ]
    state_selection = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("monitoring", "Monitoring"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    name = fields.Char(required=True, tracking=True)
    partner_id = fields.Many2one("res.partner", required=True, tracking=True, domain=[("is_company", "=", True)])
    contract_id = fields.Many2one("helpdesk.support.contract", tracking=True, domain="[('partner_id', '=', partner_id)]")
    renewal_id = fields.Many2one("helpdesk.contract.renewal", tracking=True, domain="[('partner_id', '=', partner_id)]")
    company_id = fields.Many2one(related="partner_id.company_id", store=True, readonly=True)
    owner_id = fields.Many2one("res.users", default=lambda self: self.env.user, tracking=True, domain=[("share", "=", False)])
    playbook_type = fields.Selection(selection=playbook_type_selection, required=True, default="quarterly_review", tracking=True)
    health_state = fields.Selection(selection=health_state_selection, required=True, default="on_track", tracking=True)
    cadence = fields.Selection(selection=cadence_selection, required=True, default="monthly", tracking=True)
    state = fields.Selection(selection=state_selection, required=True, default="draft", tracking=True)
    next_action_date = fields.Date(required=True, tracking=True)
    last_action_date = fields.Date(tracking=True)
    last_activity_scheduled_date = fields.Date(readonly=True, tracking=True)
    action_count = fields.Integer(compute="_compute_action_count")
    success_goal = fields.Text(tracking=True)
    risk_note = fields.Text(tracking=True)
    action_plan = fields.Html()

    def _compute_action_count(self):
        for record in self:
            record.action_count = len(record.activity_ids)

    def _schedule_success_activity(self):
        todo = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        if not todo or not self.owner_id:
            return
        existing = self.activity_ids.filtered(
            lambda activity: activity.activity_type_id == todo and activity.date_deadline == self.next_action_date
        )
        if existing:
            return
        self.activity_schedule(
            activity_type_id=todo.id,
            user_id=self.owner_id.id,
            date_deadline=self.next_action_date,
            summary=_("Customer success playbook due: %(name)s") % {"name": self.display_name},
            note=self.success_goal or self.risk_note or self.name,
        )
        self.last_activity_scheduled_date = self.next_action_date

    def action_activate(self):
        for record in self:
            record.write({"state": "active"})
            record._schedule_success_activity()
        return True

    def action_mark_monitoring(self):
        self.write({"state": "monitoring", "last_action_date": fields.Date.context_today(self)})
        return True

    def action_mark_done(self):
        self.write({"state": "done", "last_action_date": fields.Date.context_today(self)})
        self.activity_ids.unlink()
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        self.activity_ids.unlink()
        return True

    @api.model
    def _cron_schedule_due_playbooks(self):
        due = self.search(
            [
                ("state", "in", ["active", "monitoring"]),
                ("next_action_date", "<=", fields.Date.context_today(self)),
            ]
        )
        for record in due:
            record._schedule_success_activity()
        return True

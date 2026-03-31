# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HelpdeskTicket(models.Model):
    """
    Consolidated ticket extension — merges all 16 OCA sub-modules:
      • helpdesk_mgmt_sla              — SLA deadline & expiry flag
      • helpdesk_type                  — ticket type field
      • helpdesk_mgmt_template         — description pre-filled from category
      • helpdesk_mgmt_assign_method    — auto-assignment on create
      • helpdesk_mgmt_rating           — customer satisfaction rating
      • helpdesk_ticket_close_inactive — (handled by team cron, ticket side)
      • helpdesk_mgmt_merge            — (wizard only, no new ticket fields)
      • helpdesk_ticket_related        — related tickets (Many2many self)
      • helpdesk_mgmt_project          — project / task link
      • helpdesk_mgmt_sale             — sale order link
      • helpdesk_mgmt_crm              — CRM lead link
      • helpdesk_mgmt_activity         — linked record activity
      • helpdesk_mgmt_timesheet        — timesheets on ticket
      • helpdesk_mgmt_stage_validation — required fields on stage change
      • helpdesk_portal_restriction    — (handled on partner/team side)
      • helpdesk_ticket_partner_response — (handled in mail.thread override)
    """
    _inherit = ["helpdesk.ticket", "rating.mixin"]
    _name = "helpdesk.ticket"

    # ────────────────────────────────────────────────────────────────────────
    # TYPE  (helpdesk_type)
    # ────────────────────────────────────────────────────────────────────────
    type_id = fields.Many2one(
        "helpdesk.ticket.type",
        string="Type",
        ondelete="restrict",
    )

    # ────────────────────────────────────────────────────────────────────────
    # SLA  (helpdesk_mgmt_sla)
    # ────────────────────────────────────────────────────────────────────────
    sla_deadline = fields.Datetime(
        string="SLA Deadline",
        readonly=True,
        store=True,
        help="Deadline computed from the applicable SLA policy.",
    )
    sla_expired = fields.Boolean(
        string="SLA Expired",
        compute="_compute_sla_expired",
        store=True,
    )

    @api.depends("sla_deadline")
    def _compute_sla_expired(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.sla_expired = bool(
                ticket.sla_deadline and ticket.sla_deadline < now and not ticket.closed
            )

    def _check_ticket_sla(self):
        """Compute/refresh the SLA deadline for this ticket."""
        self.ensure_one()
        if not self.team_id.use_sla:
            return
        applicable_slas = self.env["helpdesk.sla"].search(
            [("team_ids", "in", self.team_id.id)]
        )
        deadline = None
        for sla in applicable_slas:
            if sla._applies_for(self):
                # Check if ticket is already in a target stage
                if self.stage_id in sla.stage_ids:
                    continue
                candidate = sla._compute_deadline(self)
                if deadline is None or candidate < deadline:
                    deadline = candidate
        self.sla_deadline = deadline

    # ────────────────────────────────────────────────────────────────────────
    # TEMPLATE  (helpdesk_mgmt_template)
    # ────────────────────────────────────────────────────────────────────────
    @api.onchange("category_id")
    def _onchange_category_template(self):
        if self.category_id and self.category_id.template_description:
            self.description = self.category_id.template_description

    # ────────────────────────────────────────────────────────────────────────
    # RATING  (helpdesk_mgmt_rating)
    # ────────────────────────────────────────────────────────────────────────
    positive_rate_percentage = fields.Integer(
        string="Positive Rating (%)",
        compute="_compute_positive_rate_percentage",
        store=True,
    )
    rating_status = fields.Selection(
        [("satisfied", "Satisfied"), ("not_satisfied", "Not Satisfied"), ("no_rating", "No Rating")],
        string="Rating Status",
        compute="_compute_rating_status",
        store=True,
    )

    @api.depends("rating_ids.rating")
    def _compute_positive_rate_percentage(self):
        for ticket in self:
            ratings = ticket.rating_ids.filtered(lambda r: r.rating is not False)
            if ratings:
                positive = ratings.filtered(lambda r: r.rating >= 5)
                ticket.positive_rate_percentage = int(len(positive) / len(ratings) * 100)
            else:
                ticket.positive_rate_percentage = 0

    @api.depends("rating_ids.rating")
    def _compute_rating_status(self):
        for ticket in self:
            ratings = ticket.rating_ids.filtered(lambda r: r.rating is not False)
            if not ratings:
                ticket.rating_status = "no_rating"
            elif ticket.positive_rate_percentage >= 50:
                ticket.rating_status = "satisfied"
            else:
                ticket.rating_status = "not_satisfied"

    def _send_ticket_rating_mail(self):
        """Send the rating request email if stage has a template configured."""
        self.ensure_one()
        template = self.stage_id.rating_mail_template_id
        if template:
            template.send_mail(self.id, force_send=True)

    # ────────────────────────────────────────────────────────────────────────
    # RELATED TICKETS  (helpdesk_ticket_related)
    # ────────────────────────────────────────────────────────────────────────
    related_ticket_ids = fields.Many2many(
        "helpdesk.ticket",
        "helpdesk_ticket_rel",
        "ticket_id",
        "related_id",
        string="Related Tickets",
    )

    def open_ticket(self):
        """Open the related tickets list view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Related Tickets"),
            "res_model": "helpdesk.ticket",
            "view_mode": "list,form",
            "domain": [("id", "in", self.related_ticket_ids.ids)],
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Auto-assign based on team method
            if record.team_id and record.team_id.assign_method != "manual" and not record.user_id:
                user = record.team_id.get_new_user()
                if user:
                    record.user_id = user
            # Compute SLA deadline
            record._check_ticket_sla()
        return records

    def write(self, vals):
        result = super().write(vals)
        # Sync bidirectional related_ticket_ids
        if "related_ticket_ids" in vals:
            for ticket in self:
                for related in ticket.related_ticket_ids:
                    if ticket not in related.related_ticket_ids:
                        related.sudo().write({
                            "related_ticket_ids": [(4, ticket.id)]
                        })
        # Trigger rating email when stage changes
        if "stage_id" in vals:
            for ticket in self:
                ticket._send_ticket_rating_mail()
                ticket._check_ticket_sla()
        return result

    # ────────────────────────────────────────────────────────────────────────
    # PROJECT  (helpdesk_mgmt_project)
    # ────────────────────────────────────────────────────────────────────────
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        compute="_compute_project_id",
        store=True,
        readonly=False,
    )
    task_id = fields.Many2one(
        "project.task",
        string="Task",
        compute="_compute_task_id",
        store=True,
        readonly=False,
    )

    @api.depends("team_id")
    def _compute_project_id(self):
        for ticket in self:
            if not ticket.project_id and ticket.team_id.default_project_id:
                ticket.project_id = ticket.team_id.default_project_id

    @api.depends("project_id")
    def _compute_task_id(self):
        for ticket in self:
            if ticket.task_id and ticket.task_id.project_id != ticket.project_id:
                ticket.task_id = False

    # Smart button counts for project
    task_count = fields.Integer(
        string="Tasks",
        compute="_compute_task_count",
    )

    def _compute_task_count(self):
        for ticket in self:
            ticket.task_count = 1 if ticket.task_id else 0

    def action_open_tasks(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Tasks"),
            "res_model": "project.task",
            "view_mode": "list,form",
            "domain": [("ticket_ids", "in", self.id)],
        }

    # ────────────────────────────────────────────────────────────────────────
    # SALE ORDER  (helpdesk_mgmt_sale)
    # ────────────────────────────────────────────────────────────────────────
    sale_order_ids = fields.Many2many(
        "sale.order",
        "helpdesk_ticket_sale_order_rel",
        "ticket_id",
        "sale_order_id",
        string="Sale Orders",
    )
    so_count = fields.Integer(
        string="Sale Orders",
        compute="_compute_so_count",
    )

    def _compute_so_count(self):
        for ticket in self:
            ticket.so_count = len(ticket.sale_order_ids)

    def action_open_sale_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sale Orders"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.sale_order_ids.ids)],
        }

    # ────────────────────────────────────────────────────────────────────────
    # CRM LEAD  (helpdesk_mgmt_crm)
    # ────────────────────────────────────────────────────────────────────────
    lead_ids = fields.One2many(
        "crm.lead",
        "ticket_id",
        string="Leads / Opportunities",
    )
    lead_count = fields.Integer(
        string="Leads",
        compute="_compute_lead_count",
    )

    def _compute_lead_count(self):
        for ticket in self:
            ticket.lead_count = len(ticket.lead_ids)

    def action_open_leads(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Leads"),
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "domain": [("ticket_id", "=", self.id)],
        }

    def action_create_lead(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Lead"),
            "res_model": "helpdesk.ticket.create.lead",
            "view_mode": "form",
            "target": "new",
            "context": {"default_ticket_id": self.id},
        }

    # ────────────────────────────────────────────────────────────────────────
    # ACTIVITY TRACKING  (helpdesk_mgmt_activity)
    # ────────────────────────────────────────────────────────────────────────
    can_create_activity = fields.Boolean(
        string="Can Create Activity",
        compute="_compute_can_create_activity",
    )
    res_model = fields.Char(string="Related Model")
    res_id = fields.Integer(string="Related Record ID")
    record_ref = fields.Reference(
        selection="_selection_record_ref",
        string="Linked Record",
        compute="_compute_record_ref",
        inverse="_inverse_record_ref",
    )
    source_activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Activity Type to Create",
    )
    date_deadline = fields.Date(string="Activity Deadline")
    next_stage_id = fields.Many2one(
        "helpdesk.ticket.stage",
        string="Move to Stage on Done",
    )
    assigned_user_id = fields.Many2one(
        "res.users",
        string="Activity Assigned To",
    )

    @api.model
    def _selection_record_ref(self):
        config = self.env["ir.config_parameter"].sudo().get_param(
            "helpdesk_mgmt_extended.available_model_ids", ""
        )
        if not config:
            return []
        try:
            import ast
            model_ids = ast.literal_eval(config)
            models_obj = self.env["ir.model"].browse(model_ids)
            return [(m.model, m.name) for m in models_obj if m.model in self.env]
        except Exception:
            return []

    def _compute_can_create_activity(self):
        for ticket in self:
            ticket.can_create_activity = bool(ticket.res_model and ticket.res_id)

    @api.depends("res_model", "res_id")
    def _compute_record_ref(self):
        for ticket in self:
            if ticket.res_model and ticket.res_id:
                try:
                    ticket.record_ref = "%s,%d" % (ticket.res_model, ticket.res_id)
                except Exception:
                    ticket.record_ref = False
            else:
                ticket.record_ref = False

    def _inverse_record_ref(self):
        for ticket in self:
            if ticket.record_ref:
                ticket.res_model = ticket.record_ref._name
                ticket.res_id = ticket.record_ref.id
            else:
                ticket.res_model = False
                ticket.res_id = False

    # ────────────────────────────────────────────────────────────────────────
    # TIMESHEET  (helpdesk_mgmt_timesheet)
    # ────────────────────────────────────────────────────────────────────────
    allow_timesheet = fields.Boolean(
        string="Allow Timesheet",
        related="team_id.allow_timesheet",
        store=True,
    )
    planned_hours = fields.Float(string="Planned Hours", default=0.0)
    timesheet_ids = fields.One2many(
        "account.analytic.line",
        "ticket_id",
        string="Timesheets",
    )
    total_hours = fields.Float(
        string="Total Hours",
        compute="_compute_timesheet_hours",
        store=True,
    )
    remaining_hours = fields.Float(
        string="Remaining Hours",
        compute="_compute_timesheet_hours",
        store=True,
    )
    progress = fields.Integer(
        string="Progress (%)",
        compute="_compute_timesheet_hours",
        store=True,
    )

    @api.depends("timesheet_ids.unit_amount", "planned_hours")
    def _compute_timesheet_hours(self):
        for ticket in self:
            total = sum(ticket.timesheet_ids.mapped("unit_amount"))
            ticket.total_hours = total
            remaining = ticket.planned_hours - total
            ticket.remaining_hours = remaining
            if ticket.planned_hours > 0:
                ticket.progress = int(min(total / ticket.planned_hours * 100, 100))
            else:
                ticket.progress = 0

    # ────────────────────────────────────────────────────────────────────────
    # STAGE VALIDATION  (helpdesk_mgmt_stage_validation)
    # ────────────────────────────────────────────────────────────────────────
    @api.constrains("stage_id")
    def _check_stage_required_fields(self):
        for ticket in self:
            stage = ticket.stage_id
            if not stage.validate_field_ids:
                continue
            empty_fields = []
            for field in stage.validate_field_ids:
                val = ticket[field.name]
                if not val and val != 0:
                    empty_fields.append(field.field_description)
            if empty_fields:
                raise ValidationError(
                    _("The following fields are required before moving to stage '%(stage)s':\n%(fields)s",
                      stage=stage.name,
                      fields="\n".join("  • " + f for f in empty_fields))
                )

    # ────────────────────────────────────────────────────────────────────────
    # DEFAULT GET — auto-assign  (helpdesk_mgmt_assign_method)
    # ────────────────────────────────────────────────────────────────────────
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if "team_id" in defaults and defaults["team_id"]:
            team = self.env["helpdesk.ticket.team"].browse(defaults["team_id"])
            if team.assign_method != "manual" and "user_id" not in defaults:
                user = team.get_new_user()
                if user:
                    defaults["user_id"] = user.id
        return defaults

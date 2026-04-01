from odoo import _, api, fields, models


class HelpdeskRenewalTarget(models.Model):
    _name = "helpdesk.renewal.target"
    _description = "Helpdesk Renewal Target"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "month_start desc, id desc"

    scope_selection = [
        ("overall", "Overall"),
        ("team", "Team"),
        ("sales_user", "Salesperson"),
    ]

    name = fields.Char(required=True, tracking=True)
    active = fields.Boolean(default=True)
    month_start = fields.Date(required=True, tracking=True)
    month_label = fields.Char(compute="_compute_month_label", store=True)
    scope_type = fields.Selection(selection=scope_selection, required=True, default="overall", tracking=True)
    team_id = fields.Many2one("helpdesk.ticket.team", tracking=True)
    sales_user_id = fields.Many2one("res.users", tracking=True, domain=[("share", "=", False)])
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, tracking=True)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    target_amount = fields.Monetary(currency_field="currency_id", required=True, tracking=True)
    budget_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    notes = fields.Html()

    _sql_constraints = [
        (
            "helpdesk_renewal_target_scope_unique",
            "unique(month_start, scope_type, team_id, sales_user_id, company_id)",
            "A renewal target already exists for this month and scope.",
        )
    ]

    @api.depends("month_start")
    def _compute_month_label(self):
        for record in self:
            record.month_label = (
                fields.Date.to_date(record.month_start).strftime("%B %Y")
                if record.month_start
                else False
            )

    @api.model
    def _ensure_forecast_feature_enabled(self):
        self.env["helpdesk.feature.config"].ensure_enabled(
            "helpdesk.renewal.forecast",
            message=_("Renewal forecast is disabled in Helpdesk feature settings."),
        )
        return True

    @api.model_create_multi
    def create(self, vals_list):
        self._ensure_forecast_feature_enabled()
        return super().create(vals_list)

    def write(self, vals):
        self._ensure_forecast_feature_enabled()
        return super().write(vals)

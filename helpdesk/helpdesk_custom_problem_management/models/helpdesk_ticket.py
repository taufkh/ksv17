from odoo import _, api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    problem_id = fields.Many2one(
        "helpdesk.problem",
        string="Problem",
        tracking=True,
        domain="[('team_id', '=', team_id)]",
    )
    problem_state = fields.Selection(
        related="problem_id.state",
        string="Problem State",
        store=True,
        readonly=True,
    )
    problem_known_error = fields.Boolean(
        related="problem_id.known_error",
        string="Known Error",
        store=True,
        readonly=True,
    )

    @api.onchange("team_id")
    def _onchange_problem_team(self):
        for ticket in self:
            if ticket.problem_id and ticket.problem_id.team_id and ticket.problem_id.team_id != ticket.team_id:
                ticket.problem_id = False

    def action_open_problem(self):
        self.ensure_one()
        if not self.problem_id:
            return False
        return self.problem_id.get_formview_action()

    def action_create_problem(self):
        self.ensure_one()
        form_view = self.env.ref("helpdesk_custom_problem_management.view_helpdesk_problem_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Create Problem"),
            "res_model": "helpdesk.problem",
            "view_mode": "form",
            "views": [(form_view.id, "form")],
            "target": "current",
            "context": {
                "default_name": self.name,
                "default_partner_id": self.commercial_partner_id.id or self.partner_id.id,
                "default_team_id": self.team_id.id,
                "default_support_asset_id": self.support_asset_id.id,
                "default_problem_owner_id": self.user_id.id or self.env.user.id,
                "default_detected_date": fields.Date.context_today(self),
                "default_impact_summary": self.description or self.name,
            },
        }

from odoo import _, fields, models
from odoo.exceptions import UserError


class PosAutoScrapApprovalWizard(models.TransientModel):
    _name = "pos.auto.scrap.approval.wizard"
    _description = "POS Auto Scrap Approval"

    session_id = fields.Many2one("pos.session", required=True, readonly=True)
    currency_id = fields.Many2one(related="session_id.auto_scrap_currency_id", readonly=True)
    projected_loss_value = fields.Monetary(
        string="Projected Loss",
        currency_field="currency_id",
        readonly=True,
        required=True,
    )
    loss_limit = fields.Monetary(
        string="Approval Limit",
        currency_field="currency_id",
        readonly=True,
        required=True,
    )
    reason = fields.Text(string="Approval Reason", required=True)

    def action_confirm(self):
        self.ensure_one()
        session = self.session_id
        if not self.user_has_groups("point_of_sale.group_pos_manager"):
            raise UserError(_("Only a POS Manager can approve auto scrap loss."))

        preview_data = session._get_auto_scrap_preview_data()
        if not preview_data["requires_manager_approval"]:
            raise UserError(_("The current projected auto scrap loss no longer requires approval."))

        session.write(
            {
                "auto_scrap_approved_by_id": self.env.user.id,
                "auto_scrap_approved_at": fields.Datetime.now(),
                "auto_scrap_approval_reason": self.reason,
                "auto_scrap_approval_estimated_value": preview_data["total_estimated_value"],
            }
        )
        session.message_post(
            body=_(
                "Auto scrap approval recorded by %(user)s for projected loss %(value).2f %(currency)s. Reason: %(reason)s",
                user=self.env.user.display_name,
                value=preview_data["total_estimated_value"],
                currency=session.auto_scrap_currency_id.name,
                reason=self.reason,
            )
        )
        return {"type": "ir.actions.act_window_close"}

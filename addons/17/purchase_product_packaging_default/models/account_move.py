from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount


class AccountMove(models.Model):
    _inherit = "account.move"

    pack_price_pending_count = fields.Integer(
        compute="_compute_pack_price_approval_counts",
        string="Pending Pack Price Approvals",
    )
    pack_price_requestable_count = fields.Integer(
        compute="_compute_pack_price_approval_counts",
        string="Pack Price Requests Ready",
    )
    can_manage_pack_price = fields.Boolean(
        compute="_compute_can_manage_pack_price",
    )

    @api.depends("invoice_line_ids.pack_price_approval_state", "invoice_line_ids.requested_pack_price", "invoice_line_ids.pack_price")
    def _compute_pack_price_approval_counts(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda line: line.display_type == "product")
            move.pack_price_pending_count = len(lines.filtered(lambda line: line.pack_price_approval_state == "pending"))
            move.pack_price_requestable_count = len(
                lines.filtered(
                    lambda line: line.requested_pack_price
                    and line.currency_id
                    and not line.currency_id.is_zero(line.requested_pack_price - line.pack_price)
                    and line.pack_price_request_reason
                    and line.pack_price_approval_state != "pending"
                )
            )

    @api.depends_context("uid")
    def _compute_can_manage_pack_price(self):
        can_manage = self.env.user.has_group("purchase.group_purchase_manager") or self.env.user.has_group(
            "account.group_account_manager"
        )
        for move in self:
            move.can_manage_pack_price = can_manage

    def _get_pack_price_approver_users(self):
        purchase_managers = self.env.ref("purchase.group_purchase_manager").users
        account_managers = self.env.ref("account.group_account_manager").users
        return (purchase_managers | account_managers).filtered(
            lambda user: user.active and not user.share and self.company_id in user.company_ids
        )

    def _get_pack_price_pending_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product" and line.pack_price_approval_state == "pending"
        )

    def _get_pack_price_request_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.requested_pack_price
            and line.currency_id
            and not line.currency_id.is_zero(line.requested_pack_price - line.pack_price)
            and line.pack_price_request_reason
            and line.pack_price_approval_state != "pending"
        )

    def _notify_pack_price_approvers(self, request_lines):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for move in self:
            approvers = move._get_pack_price_approver_users()
            if not approvers:
                continue
            message = _(
                "Pack price approval requested on vendor bill %s by %s for %s line(s).",
                move.display_name,
                self.env.user.display_name,
                len(request_lines),
            )
            move.message_post(body=message, partner_ids=approvers.partner_id.ids)
            for approver in approvers:
                existing_activity = move.activity_ids.filtered(
                    lambda activity: activity.user_id == approver
                    and activity.activity_type_id == activity_type
                    and activity.summary == _("Pack Price Approval")
                )[:1]
                if existing_activity:
                    continue
                move.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=approver.id,
                    summary=_("Pack Price Approval"),
                    note=message,
                )

    def action_request_pack_price_approval(self):
        for move in self:
            if move.move_type != "in_invoice" or move.state != "draft":
                raise UserError(_("Pack price approval can only be requested on draft vendor bills."))
            request_lines = move._get_pack_price_request_lines()
            if not request_lines:
                raise UserError(_("There are no pack price changes ready to request approval."))
            request_lines.write(
                {
                    "pack_price_approval_state": "pending",
                    "pack_price_requested_by_id": self.env.user.id,
                    "pack_price_requested_at": fields.Datetime.now(),
                }
            )
            move._notify_pack_price_approvers(request_lines)
        return True

    def action_approve_pack_price_changes(self):
        if not self.env.user.has_group("purchase.group_purchase_manager") and not self.env.user.has_group(
            "account.group_account_manager"
        ):
            raise UserError(_("Only managers can approve vendor bill pack price changes."))
        for move in self:
            pending_lines = move._get_pack_price_pending_lines()
            if not pending_lines:
                raise UserError(_("There are no pending pack price changes to approve."))
            for line in pending_lines:
                old_pack_price = line.pack_price
                line.with_context(allow_pack_price_manager_write=True).write(
                    {
                        "pack_price": line.requested_pack_price,
                        "pack_price_approval_state": "approved",
                        "pack_price_approved_by_id": self.env.user.id,
                        "pack_price_approved_at": fields.Datetime.now(),
                    }
                )
                move.message_post(
                    body=_(
                        "Pack price approved for %s: %s -> %s.",
                        line.product_id.display_name,
                        format_amount(self.env, old_pack_price, move.currency_id),
                        format_amount(self.env, line.pack_price, move.currency_id),
                    )
                )
            move.activity_ids.filtered(
                lambda activity: activity.summary == _("Pack Price Approval")
            ).action_feedback(feedback=_("Pack price changes approved."))
        return True

    def action_reject_pack_price_changes(self):
        if not self.env.user.has_group("purchase.group_purchase_manager") and not self.env.user.has_group(
            "account.group_account_manager"
        ):
            raise UserError(_("Only managers can reject vendor bill pack price changes."))
        for move in self:
            pending_lines = move._get_pack_price_pending_lines()
            if not pending_lines:
                raise UserError(_("There are no pending pack price changes to reject."))
            pending_lines.write(
                {
                    "pack_price_approval_state": "rejected",
                    "pack_price_approved_by_id": False,
                    "pack_price_approved_at": False,
                }
            )
            move.message_post(
                body=_(
                    "Pack price approval rejected by %s.",
                    self.env.user.display_name,
                )
            )
            move.activity_ids.filtered(
                lambda activity: activity.summary == _("Pack Price Approval")
            ).action_feedback(feedback=_("Pack price changes rejected."))
        return True

    def action_post(self):
        for move in self.filtered(lambda record: record.move_type == "in_invoice"):
            if move._get_pack_price_pending_lines():
                raise UserError(_("You cannot post a vendor bill while pack price changes are pending approval."))
        return super().action_post()

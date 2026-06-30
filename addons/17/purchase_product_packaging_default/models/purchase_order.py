import hashlib
import json

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    approval_signature_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
        ],
        string="Approval Signature State",
        default="draft",
        copy=False,
        readonly=True,
    )
    requested_by_id = fields.Many2one("res.users", string="Requested By", copy=False, readonly=True)
    requested_by_name = fields.Char(string="Requested By Name", copy=False, readonly=True)
    requested_at = fields.Datetime(string="Requested At", copy=False, readonly=True)
    requested_signature = fields.Binary(string="Requested Signature", copy=False, attachment=True, readonly=True)
    approved_by_id = fields.Many2one("res.users", string="Approved By", copy=False, readonly=True)
    approved_by_name = fields.Char(string="Approved By Name", copy=False, readonly=True)
    approved_at = fields.Datetime(string="Approved At", copy=False, readonly=True)
    approved_signature = fields.Binary(string="Approved Signature", copy=False, attachment=True, readonly=True)
    approval_snapshot_hash = fields.Char(string="Approval Snapshot Hash", copy=False, readonly=True)

    def _get_approval_manager_users(self):
        purchase_managers = self.env.ref("purchase.group_purchase_manager").users
        return purchase_managers.filtered(lambda user: user.active and not user.share and self.company_id in user.company_ids)

    def _get_signature_user_binary(self, user):
        if "sign_signature" in user._fields:
            return user.sign_signature
        return False

    def _get_signature_snapshot_payload(self):
        self.ensure_one()
        return {
            "partner_id": self.partner_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "date_order": fields.Datetime.to_string(self.date_order) if self.date_order else False,
            "order_line": [
                {
                    "display_type": line.display_type,
                    "product_id": line.product_id.id,
                    "name": line.name,
                    "product_qty": line.product_qty,
                    "product_uom_id": line.product_uom.id,
                    "product_packaging_id": line.product_packaging_id.id,
                    "product_packaging_qty": line.product_packaging_qty,
                    "pack_price": line.pack_price,
                    "price_unit": line.price_unit,
                    "taxes_id": sorted(line.taxes_id.ids),
                    "date_planned": fields.Datetime.to_string(line.date_planned) if line.date_planned else False,
                }
                for line in self.order_line.sorted("sequence")
            ],
        }

    def _compute_signature_snapshot_hash(self):
        self.ensure_one()
        payload = self._get_signature_snapshot_payload()
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def _has_signature_snapshot_changed(self):
        self.ensure_one()
        return bool(self.approval_snapshot_hash and self.approval_snapshot_hash != self._compute_signature_snapshot_hash())

    def _get_po_approval_activity_summary(self):
        return _("Purchase Order Approval")

    def _notify_po_approvers(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for order in self:
            approvers = order._get_approval_manager_users()
            if not approvers:
                continue
            message = _(
                "Purchase order %s requested approval by %s.",
                order.name,
                order.requested_by_name or self.env.user.display_name,
            )
            order.message_post(body=message, partner_ids=approvers.partner_id.ids)
            for approver in approvers:
                existing_activity = order.activity_ids.filtered(
                    lambda activity: activity.user_id == approver
                    and activity.activity_type_id == activity_type
                    and activity.summary == order._get_po_approval_activity_summary()
                )[:1]
                if existing_activity:
                    continue
                order.activity_schedule(
                    "mail.mail_activity_data_todo",
                    user_id=approver.id,
                    summary=order._get_po_approval_activity_summary(),
                    note=message,
                )

    def _clear_po_approval_activities(self, feedback):
        self.activity_ids.filtered(lambda activity: activity.summary == self._get_po_approval_activity_summary()).action_feedback(
            feedback=feedback
        )

    def _reset_signature_approval(self, reason):
        for order in self.filtered(lambda record: record.approval_signature_state in ("pending_approval", "approved")):
            vals = {
                "approval_signature_state": "draft",
                "requested_by_id": False,
                "requested_by_name": False,
                "requested_at": False,
                "requested_signature": False,
                "approved_by_id": False,
                "approved_by_name": False,
                "approved_at": False,
                "approved_signature": False,
                "approval_snapshot_hash": False,
            }
            if order.state == "to approve":
                vals["state"] = "draft"
            order.with_context(skip_po_signature_invalidation=True).write(vals)
            order.message_post(body=reason)
            order._clear_po_approval_activities(_("Purchase order approval reset."))

    def _open_signature_wizard(self, action_type):
        self.ensure_one()
        view = self.env.ref("purchase_product_packaging_default.view_purchase_order_signature_wizard_form")
        return {
            "type": "ir.actions.act_window",
            "name": _("Purchase Order Signature"),
            "res_model": "purchase.order.signature.wizard",
            "view_mode": "form",
            "views": [(view.id, "form")],
            "target": "new",
            "context": {
                "default_purchase_order_id": self.id,
                "default_action_type": action_type,
                "default_signer_name": self.env.user.display_name,
                "default_signature": self._get_signature_user_binary(self.env.user),
            },
        }

    def action_open_request_signature_wizard(self):
        self.ensure_one()
        if self.state not in ("draft", "sent"):
            raise UserError(_("Approval can only be requested from an RFQ in Draft or RFQ Sent state."))
        return self._open_signature_wizard("request")

    def action_open_approval_signature_wizard(self):
        self.ensure_one()
        if not self.env.user.has_group("purchase.group_purchase_manager"):
            raise UserError(_("Only Purchase Managers can approve and confirm purchase orders."))
        if self.state != "to approve":
            raise UserError(_("Only purchase orders waiting for approval can be approved."))
        if self.approval_signature_state != "pending_approval":
            raise UserError(_("This purchase order must be requested and signed before approval."))
        if self._has_signature_snapshot_changed():
            raise UserError(_("This purchase order has changed since approval was requested. Please request approval again."))
        return self._open_signature_wizard("approve")

    def action_sign_request_approval(self, signature):
        for order in self:
            if order.state not in ("draft", "sent"):
                raise UserError(_("Approval can only be requested from an RFQ in Draft or RFQ Sent state."))
            if not signature:
                raise UserError(_("A requester signature is required."))
            order_vals = {
                "requested_by_id": self.env.user.id,
                "requested_by_name": self.env.user.display_name,
                "requested_at": fields.Datetime.now(),
                "requested_signature": signature,
                "approved_by_id": False,
                "approved_by_name": False,
                "approved_at": False,
                "approved_signature": False,
                "approval_signature_state": "pending_approval",
                "approval_snapshot_hash": order._compute_signature_snapshot_hash(),
                "state": "to approve",
            }
            order.with_context(skip_po_signature_invalidation=True).write(order_vals)
            order._notify_po_approvers()
        return True

    def action_sign_approve_order(self, signature):
        if not self.env.user.has_group("purchase.group_purchase_manager"):
            raise UserError(_("Only Purchase Managers can approve and confirm purchase orders."))
        for order in self:
            if order.state != "to approve":
                raise UserError(_("Only purchase orders waiting for approval can be approved."))
            if order.approval_signature_state != "pending_approval":
                raise UserError(_("This purchase order must be requested and signed before approval."))
            if order._has_signature_snapshot_changed():
                raise UserError(_("This purchase order has changed since approval was requested. Please request approval again."))
            if not signature:
                raise UserError(_("An approver signature is required."))
            order.with_context(skip_po_signature_invalidation=True).write(
                {
                    "approved_by_id": self.env.user.id,
                    "approved_by_name": self.env.user.display_name,
                    "approved_at": fields.Datetime.now(),
                    "approved_signature": signature,
                    "approval_signature_state": "approved",
                }
            )
            order.with_context(skip_po_signature_checks=True).button_approve()
            order._clear_po_approval_activities(_("Purchase order approved."))
        return True

    def button_confirm(self):
        if not self.env.context.get("skip_po_signature_checks"):
            blocked_orders = self.filtered(lambda order: order.state in ("draft", "sent"))
            if blocked_orders:
                raise UserError(_("Use Sign & Request Approval before confirming a purchase order."))
        return super().button_confirm()

    def button_approve(self, force=False):
        if not self.env.context.get("skip_po_signature_checks"):
            blocked_orders = self.filtered(
                lambda order: order.state == "to approve" and order.approval_signature_state != "approved"
            )
            if blocked_orders:
                raise UserError(_("Use Confirm Order and sign approval before approving this purchase order."))
        return super().button_approve(force=force)

    def write(self, vals):
        tracked_fields = {"partner_id", "currency_id", "date_order"}
        should_invalidate = (
            not self.env.context.get("skip_po_signature_invalidation")
            and bool(tracked_fields.intersection(vals))
        )
        result = super().write(vals)
        if should_invalidate:
            self.filtered(lambda order: order.state in ("draft", "sent", "to approve"))._reset_signature_approval(
                _("Approval was reset because the purchase order was updated after the approval request.")
            )
        return result


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _should_reset_po_signature(self):
        return self.order_id.filtered(
            lambda order: order.approval_signature_state in ("pending_approval", "approved")
            and order.state in ("draft", "sent", "to approve")
        )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("skip_po_signature_invalidation"):
            lines._should_reset_po_signature()._reset_signature_approval(
                _("Approval was reset because purchase order lines were changed after the approval request.")
            )
        return lines

    def write(self, vals):
        tracked_fields = {
            "display_type",
            "name",
            "product_id",
            "product_qty",
            "product_uom",
            "product_packaging_id",
            "product_packaging_qty",
            "pack_price",
            "price_unit",
            "taxes_id",
            "date_planned",
        }
        should_invalidate = not self.env.context.get("skip_po_signature_invalidation") and bool(
            tracked_fields.intersection(vals)
        )
        result = super().write(vals)
        if should_invalidate:
            self._should_reset_po_signature()._reset_signature_approval(
                _("Approval was reset because purchase order lines were changed after the approval request.")
            )
        return result

    def unlink(self):
        orders = self._should_reset_po_signature()
        result = super().unlink()
        if not self.env.context.get("skip_po_signature_invalidation"):
            orders._reset_signature_approval(
                _("Approval was reset because purchase order lines were changed after the approval request.")
            )
        return result

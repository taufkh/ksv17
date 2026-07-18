from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosBackendVoidOrderWizard(models.TransientModel):
    _name = "pos.backend.void.order.wizard"
    _description = "POS Backend Void Order Wizard"

    order_id = fields.Many2one("pos.order", required=True, readonly=True)
    company_id = fields.Many2one(related="order_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    amount_total = fields.Monetary(readonly=True)
    payment_snapshot = fields.Text(readonly=True)
    reason = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env["pos.order"].browse(self.env.context.get("active_id"))
        if not order.exists():
            return values

        order._check_backend_void_allowed()
        values.update(
            {
                "order_id": order.id,
                "amount_total": order.amount_total,
                "payment_snapshot": order._format_payment_lines_snapshot(
                    order._get_positive_settlement_payment_lines()
                ),
            }
        )
        return values

    def _check_finance_access(self):
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can void POS orders from the backend."))

    def action_apply_void(self):
        self.ensure_one()
        self._check_finance_access()
        if not self.reason or not self.reason.strip():
            raise ValidationError(_("Void reason is required."))

        refund_order = self.order_id.action_backend_void_order(self.reason)
        return {
            "name": _("Void Refund Order"),
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "view_mode": "form",
            "res_id": refund_order.id,
            "target": "current",
        }

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosBackendPaymentRevisionWizard(models.TransientModel):
    _name = "pos.backend.payment.revision.wizard"
    _description = "POS Backend Payment Revision Wizard"

    order_id = fields.Many2one("pos.order", required=True, readonly=True)
    company_id = fields.Many2one(related="order_id.company_id", readonly=True)
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    reason = fields.Text(required=True)
    target_amount = fields.Monetary(readonly=True)
    line_ids = fields.One2many(
        "pos.backend.payment.revision.wizard.line",
        "wizard_id",
        string="Payment Lines",
        copy=False,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env["pos.order"].browse(self.env.context.get("active_id"))
        if not order.exists():
            return values

        order._check_backend_payment_revision_allowed()
        payment_lines = order._get_non_zero_payment_lines().sorted(key=lambda line: line.id)
        values.update(
            {
                "order_id": order.id,
                "target_amount": order.currency_id.round(sum(payment_lines.mapped("amount"))),
                "line_ids": [
                    Command.create(
                        {
                            "payment_id": line.id,
                            "payment_method_id": line.payment_method_id.id,
                            "amount": line.amount,
                        }
                    )
                    for line in payment_lines
                ],
            }
        )
        return values

    def _check_finance_access(self):
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can revise POS payment lines from the backend."))

    def _validate_revision_lines(self):
        self.ensure_one()
        self._check_finance_access()
        self.order_id._check_backend_payment_revision_allowed()

        if not self.line_ids:
            raise ValidationError(_("Add at least one payment line."))

        rounded_amounts = []
        for line in self.line_ids:
            rounded_amount = self.currency_id.round(line.amount or 0)
            if self.currency_id.is_zero(rounded_amount):
                raise ValidationError(_("Payment line amounts must be greater than zero."))
            if rounded_amount < 0:
                raise ValidationError(_("Payment line amounts cannot be negative."))
            if not line.payment_method_id:
                raise ValidationError(_("Every payment line must have a payment method."))
            allowed_methods = line.wizard_id.order_id._get_backend_changeable_payment_methods()
            if line.payment_method_id not in allowed_methods:
                raise ValidationError(
                    _("Payment method %(method)s is not allowed for this POS order.")
                    % {"method": line.payment_method_id.display_name}
                )
            rounded_amounts.append(rounded_amount)

        total_amount = self.currency_id.round(sum(rounded_amounts))
        if total_amount != self.currency_id.round(self.target_amount):
            raise ValidationError(
                _(
                    "Total payment amount must stay equal to %(expected)s. Current total is %(actual)s."
                )
                % {
                    "expected": self.currency_id.round(self.target_amount),
                    "actual": total_amount,
                }
            )

    def action_apply_revision(self):
        self.ensure_one()
        self._validate_revision_lines()
        policy_info = self.order_id._check_backend_payment_revision_allowed()
        order = self.order_id.sudo()
        existing_lines = order._get_non_zero_payment_lines().sorted(key=lambda line: line.id)
        wizard_lines = self.line_ids.sorted(key=lambda line: (line.sequence, line.id))
        old_snapshot = order._format_payment_lines_snapshot(existing_lines)
        new_snapshot = order._format_payment_lines_snapshot(wizard_lines)
        log_values = {
            "change_type": "payment_method",
            "change_origin": "backend_finance",
            "payment_amount": self.target_amount,
            "change_reason": self.reason,
            "old_snapshot": old_snapshot,
            "new_snapshot": new_snapshot,
            "policy_status": policy_info["policy_status"],
            "policy_note": policy_info["policy_note"],
        }
        if len(existing_lines) == 1 and len(wizard_lines) == 1:
            log_values.update(
                {
                    "old_payment_method_id": existing_lines.payment_method_id.id,
                    "new_payment_method_id": wizard_lines.payment_method_id.id,
                }
            )

        for payment in order.payment_ids.filtered(lambda payment: order.currency_id.is_zero(payment.amount)):
            payment.unlink()

        reusable_count = min(len(existing_lines), len(wizard_lines))
        for index in range(reusable_count):
            payment = existing_lines[index]
            wizard_line = wizard_lines[index]
            payment.write(
                {
                    "payment_method_id": wizard_line.payment_method_id.id,
                    "amount": wizard_line.amount,
                }
            )

        for payment in existing_lines[reusable_count:]:
            payment.unlink()

        for wizard_line in wizard_lines[reusable_count:]:
            self.env["pos.payment"].sudo().create(
                {
                    "pos_order_id": order.id,
                    "payment_date": order.date_order or fields.Datetime.now(),
                    "payment_method_id": wizard_line.payment_method_id.id,
                    "amount": wizard_line.amount,
                }
            )

        order.write(
            {
                "last_payment_method_change_at": fields.Datetime.now(),
                "last_payment_method_change_by_id": self.env.user.id,
            }
        )

        order._create_revision_log(log_values)

        if hasattr(order, "message_post"):
            order.message_post(
                body=_("Backend payment revision executed by %(user)s. Reason: %(reason)s")
                % {
                    "user": self.env.user.display_name,
                    "reason": self.reason,
                }
            )

        return {"type": "ir.actions.act_window_close"}


class PosBackendPaymentRevisionWizardLine(models.TransientModel):
    _name = "pos.backend.payment.revision.wizard.line"
    _description = "POS Backend Payment Revision Wizard Line"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        "pos.backend.payment.revision.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    payment_id = fields.Many2one("pos.payment", readonly=True)
    payment_method_id = fields.Many2one(
        "pos.payment.method",
        required=True,
    )
    available_payment_method_ids = fields.Many2many(
        "pos.payment.method",
        compute="_compute_available_payment_method_ids",
    )
    amount = fields.Monetary(required=True, currency_field="currency_id")
    currency_id = fields.Many2one(related="wizard_id.currency_id", readonly=True)

    @api.depends("wizard_id.order_id")
    def _compute_available_payment_method_ids(self):
        for line in self:
            methods = line.wizard_id.order_id._get_backend_changeable_payment_methods()
            line.available_payment_method_ids = [Command.set(methods.ids)]

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    revision_change_log_ids = fields.One2many(
        "pos.revision.change.log",
        "order_id",
        string="POS Revision Logs",
        readonly=True,
    )
    payment_method_change_log_ids = fields.One2many(
        "pos.payment.method.change.log",
        "order_id",
        string="Payment Method Change Logs",
        readonly=True,
    )
    sale_channel_change_log_ids = fields.One2many(
        "pos.sale.channel.change.log",
        "order_id",
        string="Sales Channel Change Logs",
        readonly=True,
    )
    revision_change_count = fields.Integer(
        string="POS Revision Change Count",
        compute="_compute_revision_change_count",
    )
    payment_method_change_count = fields.Integer(
        string="Payment Method Change Count",
        compute="_compute_payment_method_change_count",
    )
    sale_channel_change_count = fields.Integer(
        string="Sales Channel Change Count",
        compute="_compute_sale_channel_change_count",
    )
    last_payment_method_change_at = fields.Datetime(
        string="Last Payment Method Change At",
        copy=False,
        readonly=True,
    )
    last_payment_method_change_by_id = fields.Many2one(
        "res.users",
        string="Last Payment Method Change By",
        copy=False,
        readonly=True,
    )
    is_voided = fields.Boolean(
        string="Voided",
        copy=False,
        readonly=True,
    )
    voided_at = fields.Datetime(
        string="Voided At",
        copy=False,
        readonly=True,
    )
    voided_by_id = fields.Many2one(
        "res.users",
        string="Voided By",
        copy=False,
        readonly=True,
    )
    void_reason = fields.Text(
        string="Void Reason",
        copy=False,
        readonly=True,
    )
    void_refund_order_id = fields.Many2one(
        "pos.order",
        string="Void Refund Order",
        copy=False,
        readonly=True,
    )
    void_origin_order_id = fields.Many2one(
        "pos.order",
        string="Voided Original Order",
        copy=False,
        readonly=True,
    )

    @api.model
    def create_from_ui(self, orders, draft=False):
        normalized_orders = [self._normalize_ui_order_payment_payload(order) for order in orders]
        results = super().create_from_ui(normalized_orders, draft=draft)
        if draft or not results:
            return results
        created_orders = self.browse([result["id"] for result in results if result.get("id")])
        created_orders._merge_duplicate_payment_lines()
        return results

    @api.depends("revision_change_log_ids")
    def _compute_revision_change_count(self):
        for order in self:
            order.revision_change_count = len(order.revision_change_log_ids)

    @api.depends("payment_method_change_log_ids")
    def _compute_payment_method_change_count(self):
        for order in self:
            order.payment_method_change_count = len(order.payment_method_change_log_ids)

    @api.depends("sale_channel_change_log_ids")
    def _compute_sale_channel_change_count(self):
        for order in self:
            order.sale_channel_change_count = len(order.sale_channel_change_log_ids)

    @api.model
    def _payment_merge_value_fields(self):
        return [
            "name",
            "payment_date",
            "card_type",
            "cardholder_name",
            "transaction_id",
            "payment_status",
            "ticket",
        ]

    @api.model
    def _payment_merge_key_fields(self):
        return [
            "payment_method_id",
            "card_type",
            "cardholder_name",
            "transaction_id",
            "payment_status",
            "ticket",
        ]

    @api.model
    def _build_payment_merge_key(self, values):
        payment_method_id = values.get("payment_method_id")
        if not payment_method_id:
            return False
        key = [payment_method_id]
        for field_name in self._payment_merge_key_fields()[1:]:
            key.append(values.get(field_name) or False)
        return tuple(key)

    @api.model
    def _normalize_ui_payment_commands(self, commands):
        if not isinstance(commands, list):
            return commands

        normalized_commands = []
        indexed_commands = {}
        merged_count = 0

        for command in commands:
            if not (
                isinstance(command, (list, tuple))
                and len(command) >= 3
                and command[0] == 0
                and isinstance(command[2], dict)
            ):
                normalized_commands.append(command)
                continue

            payment_values = dict(command[2])
            merge_key = self._build_payment_merge_key(payment_values)
            if not merge_key:
                normalized_commands.append([command[0], command[1], payment_values])
                continue

            existing_index = indexed_commands.get(merge_key)
            if existing_index is None:
                normalized_commands.append([command[0], command[1], payment_values])
                indexed_commands[merge_key] = len(normalized_commands) - 1
                continue

            existing_values = normalized_commands[existing_index][2]
            existing_values["amount"] = (existing_values.get("amount") or 0.0) + (
                payment_values.get("amount") or 0.0
            )
            for field_name in self._payment_merge_value_fields():
                if payment_values.get(field_name):
                    existing_values[field_name] = payment_values[field_name]
            merged_count += 1

        if merged_count:
            _logger.warning(
                "Collapsed %s duplicate POS payment command(s) in incoming UI payload.",
                merged_count,
            )
            return normalized_commands
        return commands

    @api.model
    def _normalize_ui_order_payment_payload(self, ui_order):
        if not isinstance(ui_order, dict):
            return ui_order

        normalized_order = dict(ui_order)
        data = normalized_order.get("data")
        if isinstance(data, dict):
            payload = dict(data)
            payload_fields = payload
        else:
            payload = normalized_order
            payload_fields = normalized_order

        changed = False
        for field_name in ("statement_ids", "payment_ids"):
            if field_name not in payload_fields:
                continue
            normalized_commands = self._normalize_ui_payment_commands(payload_fields[field_name])
            if normalized_commands is not payload_fields[field_name]:
                payload[field_name] = normalized_commands
                changed = True

        if changed and isinstance(data, dict):
            normalized_order["data"] = payload
        return normalized_order

    def _merge_duplicate_payment_lines(self):
        merge_fields = self._payment_merge_value_fields()
        for order in self:
            grouped_lines = {}
            for payment in order.payment_ids.sorted(key=lambda line: line.id):
                merge_key = order._build_payment_merge_key(
                    {
                        "payment_method_id": payment.payment_method_id.id,
                        "card_type": getattr(payment, "card_type", False),
                        "cardholder_name": getattr(payment, "cardholder_name", False),
                        "transaction_id": getattr(payment, "transaction_id", False),
                        "payment_status": getattr(payment, "payment_status", False),
                        "ticket": getattr(payment, "ticket", False),
                    }
                )
                if not merge_key:
                    continue
                grouped_lines.setdefault(merge_key, []).append(payment)

            for merge_key, payment_lines in grouped_lines.items():
                if len(payment_lines) <= 1:
                    continue

                keeper = payment_lines[0]
                duplicates = payment_lines[1:]
                payment_line_list = list(payment_lines)
                update_values = {
                    "amount": sum(payment_lines.mapped("amount")),
                }
                for field_name in merge_fields:
                    if field_name not in keeper._fields:
                        continue
                    latest_value = next(
                        (getattr(line, field_name) for line in reversed(payment_line_list) if getattr(line, field_name)),
                        False,
                    )
                    if latest_value:
                        update_values[field_name] = latest_value
                keeper.write(update_values)
                duplicates.unlink()
                _logger.warning(
                    "Collapsed %s duplicate payment line(s) on POS order %s for payment method %s.",
                    len(duplicates),
                    order.pos_reference or order.name or order.id,
                    keeper.payment_method_id.display_name,
                )

    def _get_non_zero_payment_lines(self):
        self.ensure_one()
        return self.payment_ids.filtered(lambda payment: not self.currency_id.is_zero(payment.amount))

    def _get_positive_settlement_payment_lines(self):
        self.ensure_one()
        payment_totals = {}
        payment_templates = {}
        for payment in self.payment_ids.sorted(key=lambda item: item.id):
            if self.currency_id.is_zero(payment.amount) or not payment.payment_method_id:
                continue
            payment_totals.setdefault(payment.payment_method_id.id, 0.0)
            payment_totals[payment.payment_method_id.id] += payment.amount
            payment_templates.setdefault(payment.payment_method_id.id, payment)

        settlement_lines = []
        for method_id, template in payment_templates.items():
            amount = self.currency_id.round(payment_totals[method_id])
            if amount <= 0 or self.currency_id.is_zero(amount):
                continue
            settlement_lines.append(
                {
                    "payment_method_id": template.payment_method_id,
                    "amount": amount,
                    "payment_date": template.payment_date,
                    "card_type": template.card_type,
                    "cardholder_name": template.cardholder_name,
                    "transaction_id": template.transaction_id,
                    "payment_status": template.payment_status,
                    "ticket": template.ticket,
                }
            )
        return settlement_lines

    def _get_backend_changeable_payment_methods(self):
        self.ensure_one()
        methods = self.config_id.payment_method_ids | self.payment_ids.mapped("payment_method_id")
        company_methods = methods.filtered(
            lambda method: not method.company_id or method.company_id == self.company_id
        )
        return company_methods.sorted(key=lambda method: ((method.name or "").lower(), method.id))

    def _format_payment_lines_snapshot(self, lines):
        self.ensure_one()
        snapshots = []
        for line in lines:
            if isinstance(line, dict):
                method = line.get("payment_method_id")
                amount = line.get("amount", 0.0)
            else:
                method = getattr(line, "payment_method_id", False)
                amount = getattr(line, "amount", 0.0)
            snapshots.append(
                "%s: %s"
                % (
                    method.display_name if method else _("Unknown"),
                    self.currency_id.symbol and ("%s%s" % (self.currency_id.symbol, self.currency_id.round(amount)))
                    or str(self.currency_id.round(amount)),
                )
            )
        return " | ".join(snapshots)

    def _create_revision_log(self, values):
        self.ensure_one()
        defaults = {
            "order_id": self.id,
            "executed_by_id": self.env.user.id,
            "change_origin": "pos_frontend",
            "policy_status": "not_applicable",
        }
        defaults.update(values)
        return self.env["pos.revision.change.log"].sudo().create(defaults)

    def _check_backend_revision_security_window(self, action_name):
        self.ensure_one()
        pin_record = self.env["pos.supervisor.pin"].sudo().get_company_pin(self.company_id)
        return pin_record.sudo().check_backend_revision_window(self, action_name)

    def _can_change_paid_order_details(self):
        self.ensure_one()
        allowed_states = {"paid", "done", "invoiced"}
        return bool(
            self.id
            and self.amount_total > 0
            and self.state in allowed_states
            and self.session_id.state != "closed"
        )

    def _check_paid_order_change_allowed(self, pos_session_id=False):
        self.ensure_one()
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise UserError(_("You are not allowed to change paid POS order details."))
        if self.amount_total <= 0:
            raise UserError(_("Only positive paid orders can be corrected."))
        if self.state not in {"paid", "done", "invoiced"}:
            raise UserError(_("Only paid POS orders can be corrected."))
        if self.session_id.state == "closed":
            raise UserError(_("Paid order details can only be corrected before the POS session is closed."))
        if pos_session_id and self.session_id.id != pos_session_id:
            raise UserError(_("You can only correct orders in the current POS session."))

    def _check_backend_payment_revision_allowed(self):
        self.ensure_one()
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can revise POS payment lines from the backend."))
        if self.amount_total <= 0:
            raise UserError(_("Only positive paid orders can be corrected."))
        if self.state not in {"paid", "done", "invoiced"}:
            raise UserError(_("Only paid POS orders can be corrected."))
        if not self._get_non_zero_payment_lines():
            raise UserError(_("This order does not have a payable POS payment line."))
        return self._check_backend_revision_security_window(_("Payment revision"))

    def _check_backend_sale_channel_revision_allowed(self):
        self.ensure_one()
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can revise POS sales channel from the backend."))
        if self.amount_total <= 0:
            raise UserError(_("Only positive paid orders can be corrected."))
        if self.state not in {"paid", "done", "invoiced"}:
            raise UserError(_("Only paid POS orders can be corrected."))
        return self._check_backend_revision_security_window(_("Sales channel revision"))

    def _check_backend_void_allowed(self):
        self.ensure_one()
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can void POS orders from the backend."))
        if self.amount_total <= 0:
            raise UserError(_("Only positive paid orders can be voided."))
        if self.state not in {"paid", "done", "invoiced"}:
            raise UserError(_("Only paid POS orders can be voided."))
        if self.is_voided:
            raise UserError(_("This POS order has already been voided."))
        if self.void_origin_order_id:
            raise UserError(_("A void refund order cannot be voided again."))
        if self.refund_orders_count or self.refunded_orders_count:
            raise UserError(
                _("This POS order already has refund activity and cannot be voided automatically.")
            )
        if not self._get_positive_settlement_payment_lines():
            raise UserError(_("This POS order does not have a positive settlement payment line."))
        if not self.config_id.current_session_id:
            raise UserError(
                _(
                    "To void this POS order, open an active session first in POS %s."
                )
                % self.config_id.display_name
            )
        return self._check_backend_revision_security_window(_("Order void"))

    def action_open_backend_void_wizard(self):
        self.ensure_one()
        self._check_backend_void_allowed()
        return {
            "name": _("Void Order"),
            "type": "ir.actions.act_window",
            "res_model": "pos.backend.void.order.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_model": "pos.order",
            },
        }

    def action_open_backend_sale_channel_revision_wizard(self):
        self.ensure_one()
        self._check_backend_sale_channel_revision_allowed()
        return {
            "name": _("Revise Sales Channel"),
            "type": "ir.actions.act_window",
            "res_model": "pos.backend.sale.channel.revision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_model": "pos.order",
            },
        }

    def action_backend_revise_sale_channel(self, new_sale_channel, reason):
        self.ensure_one()
        policy_info = self._check_backend_sale_channel_revision_allowed()
        if not reason or not reason.strip():
            raise ValidationError(_("Revision reason is required."))
        if not new_sale_channel or not new_sale_channel.exists():
            raise UserError(_("The selected sales channel does not exist."))

        allowed_channels = self._get_changeable_sale_channels() | self.sale_channel_id | new_sale_channel
        if new_sale_channel not in allowed_channels:
            raise UserError(_("The selected sales channel is not allowed for this POS order."))
        if new_sale_channel == self.sale_channel_id:
            raise UserError(_("The new sales channel must be different from the current one."))

        old_sale_channel = self.sale_channel_id
        self.write({"sale_channel_id": new_sale_channel.id})
        if "sale_channel_id" in self.lines._fields:
            self.lines.write({"sale_channel_id": new_sale_channel.id})

        self._create_revision_log(
            {
                "change_type": "sale_channel",
                "change_origin": "backend_finance",
                "old_sale_channel_id": old_sale_channel.id if old_sale_channel else False,
                "new_sale_channel_id": new_sale_channel.id,
                "change_reason": reason.strip(),
                "old_snapshot": old_sale_channel.display_name or _("Unassigned"),
                "new_snapshot": new_sale_channel.display_name,
                "policy_status": policy_info["policy_status"],
                "policy_note": policy_info["policy_note"],
            }
        )

        if hasattr(self, "message_post"):
            self.message_post(
                body=_(
                    "Backend sales channel revision executed by %(user)s. From %(old)s to %(new)s. Reason: %(reason)s"
                )
                % {
                    "user": self.env.user.display_name,
                    "old": old_sale_channel.display_name or _("Unassigned"),
                    "new": new_sale_channel.display_name,
                    "reason": reason.strip(),
                }
            )

        return self

    def action_view_void_refund_order(self):
        self.ensure_one()
        if not self.void_refund_order_id:
            raise UserError(_("This POS order does not have a void refund order yet."))
        return {
            "name": _("Void Refund Order"),
            "type": "ir.actions.act_window",
            "res_model": "pos.order",
            "view_mode": "form",
            "res_id": self.void_refund_order_id.id,
            "target": "current",
        }

    def action_backend_void_order(self, reason):
        self.ensure_one()
        policy_info = self._check_backend_void_allowed()
        if not reason or not reason.strip():
            raise ValidationError(_("Void reason is required."))

        refund_order = self.sudo()._refund()
        refund_order = refund_order[:1]
        now = fields.Datetime.now()
        source_payments = self._get_positive_settlement_payment_lines()
        original_snapshot = self._format_payment_lines_snapshot(source_payments)

        refund_order.write(
            {
                "void_origin_order_id": self.id,
                "to_invoice": bool(self.account_move),
            }
        )

        for payment in source_payments:
            refund_order.add_payment(
                {
                    "pos_order_id": refund_order.id,
                    "payment_date": now,
                    "payment_method_id": payment["payment_method_id"].id,
                    "amount": -payment["amount"],
                    "card_type": payment.get("card_type"),
                    "cardholder_name": payment.get("cardholder_name"),
                    "transaction_id": payment.get("transaction_id"),
                    "payment_status": payment.get("payment_status"),
                    "ticket": payment.get("ticket"),
                }
            )

        refund_order.action_pos_order_paid()
        refund_order._create_order_picking()
        refund_order._compute_total_cost_in_real_time()
        if refund_order.to_invoice:
            refund_order._generate_pos_order_invoice()

        refund_snapshot = refund_order._format_payment_lines_snapshot(
            refund_order._get_non_zero_payment_lines().sorted(key=lambda payment: payment.id)
        )

        self.write(
            {
                "is_voided": True,
                "voided_at": now,
                "voided_by_id": self.env.user.id,
                "void_reason": reason.strip(),
                "void_refund_order_id": refund_order.id,
            }
        )

        self._create_revision_log(
            {
                "change_type": "order_void",
                "change_origin": "backend_finance",
                "related_order_id": refund_order.id,
                "payment_amount": self.amount_total,
                "change_reason": reason.strip(),
                "old_snapshot": original_snapshot,
                "new_snapshot": refund_snapshot,
                "policy_status": policy_info["policy_status"],
                "policy_note": policy_info["policy_note"],
            }
        )

        if hasattr(self, "message_post"):
            self.message_post(
                body=_(
                    "POS order voided by %(user)s. Refund order: %(refund)s. Reason: %(reason)s"
                )
                % {
                    "user": self.env.user.display_name,
                    "refund": refund_order.display_name,
                    "reason": reason.strip(),
                }
            )
        if hasattr(refund_order, "message_post"):
            refund_order.message_post(
                body=_(
                    "This refund order was created automatically as a backend void of %(order)s by %(user)s. Reason: %(reason)s"
                )
                % {
                    "order": self.display_name,
                    "user": self.env.user.display_name,
                    "reason": reason.strip(),
                }
            )

        return refund_order

    def action_open_backend_payment_revision_wizard(self):
        self.ensure_one()
        self._check_backend_payment_revision_allowed()
        return {
            "name": _("Revise Payment"),
            "type": "ir.actions.act_window",
            "res_model": "pos.backend.payment.revision.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "active_model": "pos.order",
            },
        }

    def _can_change_payment_method(self):
        self.ensure_one()
        return self._can_change_paid_order_details() and len(self._get_non_zero_payment_lines()) == 1

    def _check_payment_method_change_allowed(self, pos_session_id=False):
        self._check_paid_order_change_allowed(pos_session_id=pos_session_id)

        non_zero_payments = self._get_non_zero_payment_lines()
        if not non_zero_payments:
            raise UserError(_("This order does not have a payable POS payment line."))
        if len(non_zero_payments) != 1:
            raise UserError(_("Only orders with a single payment line can be corrected."))
        return non_zero_payments[0]

    def _get_changeable_sale_channels(self):
        self.ensure_one()
        return self.env["pos.sale.channel"].search(
            [
                ("active", "=", True),
                ("id", "!=", self.sale_channel_id.id),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ],
            order="sequence, id",
        )

    def _get_sale_channel_ui_data(self):
        self.ensure_one()
        return {
            "sale_channel_id": self.sale_channel_id.id or False,
            "sale_channel_label": self.sale_channel_id.name or "",
            "sale_channel_change_allowed": self._can_change_paid_order_details(),
        }

    def _get_changeable_payment_methods(self):
        self.ensure_one()
        payment_line = self._get_non_zero_payment_lines()[:1]
        current_method = payment_line.payment_method_id if payment_line else self.env["pos.payment.method"]
        methods = self.config_id.payment_method_ids.filtered(
            lambda method: method != current_method and not method.use_payment_terminal
        )
        return methods.sorted(key=lambda method: ((method.name or "").lower(), method.id))

    def _get_payment_method_ui_data(self):
        self.ensure_one()
        payments = self._get_non_zero_payment_lines().sorted(key=lambda payment: payment.id)
        method_names = payments.mapped("payment_method_id.name")
        current_method = payments[:1].payment_method_id
        return {
            "payment_method_names": method_names,
            "payment_method_label": ", ".join(method_names) if method_names else "",
            "payment_line_count": len(payments),
            "payment_method_change_allowed": self._can_change_payment_method(),
            "payment_method_id": current_method.id if current_method else False,
        }

    def _export_for_ui(self, order):
        values = super()._export_for_ui(order)
        values.update(order._get_payment_method_ui_data())
        values.update(order._get_sale_channel_ui_data())
        return values

    @api.model
    def get_payment_method_change_data(self, order_id, pos_session_id=False):
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("The selected order no longer exists."))

        payment_line = order._check_payment_method_change_allowed(pos_session_id=pos_session_id)
        return {
            "order": order._get_payment_method_ui_data(),
            "current_payment_method_name": payment_line.payment_method_id.name,
            "current_payment_amount": payment_line.amount,
            "payment_methods": [
                {
                    "id": method.id,
                    "name": method.name,
                }
                for method in order._get_changeable_payment_methods()
            ],
        }

    @api.model
    def get_sale_channel_change_data(self, order_id, pos_session_id=False):
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("The selected order no longer exists."))

        order._check_paid_order_change_allowed(pos_session_id=pos_session_id)
        return {
            "order": order._get_sale_channel_ui_data(),
            "current_sale_channel_name": order.sale_channel_id.name or _("Unassigned"),
            "sale_channels": [
                {
                    "id": channel.id,
                    "name": channel.name,
                }
                for channel in order._get_changeable_sale_channels()
            ],
        }

    @api.model
    def change_payment_method_from_pos(self, order_id, new_payment_method_id, supervisor_pin, pos_session_id=False):
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("The selected order no longer exists."))

        payment_line = order._check_payment_method_change_allowed(pos_session_id=pos_session_id)
        new_payment_method = self.env["pos.payment.method"].browse(new_payment_method_id)
        if not new_payment_method.exists():
            raise UserError(_("The selected payment method does not exist."))
        if new_payment_method == payment_line.payment_method_id:
            raise UserError(_("The new payment method must be different from the current one."))
        if new_payment_method not in order._get_changeable_payment_methods():
            raise UserError(_("The selected payment method is not allowed for this POS order."))

        pin_record = self.env["pos.supervisor.pin"].sudo().get_company_pin(order.company_id)
        used_pin_masked = pin_record.sudo().consume_pin(supervisor_pin, self.env.user)

        old_payment_method = payment_line.payment_method_id
        payment_line.write({"payment_method_id": new_payment_method.id})
        order.write(
            {
                "last_payment_method_change_at": fields.Datetime.now(),
                "last_payment_method_change_by_id": self.env.user.id,
            }
        )
        self._create_revision_log(
            {
                "change_type": "payment_method",
                "change_origin": "pos_frontend",
                "old_payment_method_id": old_payment_method.id,
                "new_payment_method_id": new_payment_method.id,
                "payment_amount": payment_line.amount,
                "change_reason": _("POS frontend correction approved with supervisor PIN."),
                "old_snapshot": order._format_payment_lines_snapshot(
                    [
                        type(
                            "SnapshotLine",
                            (),
                            {
                                "payment_method_id": old_payment_method,
                                "amount": payment_line.amount,
                            },
                        )()
                    ]
                ),
                "new_snapshot": order._format_payment_lines_snapshot(
                    [
                        type(
                            "SnapshotLine",
                            (),
                            {
                                "payment_method_id": new_payment_method,
                                "amount": payment_line.amount,
                            },
                        )()
                    ]
                ),
                "used_pin_masked": used_pin_masked,
            }
        )
        self.env["pos.payment.method.change.log"].sudo().create(
            {
                "order_id": order.id,
                "old_payment_method_id": old_payment_method.id,
                "new_payment_method_id": new_payment_method.id,
                "payment_amount": payment_line.amount,
                "executed_by_id": self.env.user.id,
                "used_pin_masked": used_pin_masked,
            }
        )

        if hasattr(order, "message_post"):
            order.message_post(
                body=_(
                    "Payment method changed from %(old)s to %(new)s by %(user)s."
                )
                % {
                    "old": old_payment_method.display_name,
                    "new": new_payment_method.display_name,
                    "user": self.env.user.display_name,
                }
            )

        return {
            "success": True,
            "order": order._get_payment_method_ui_data(),
        }

    @api.model
    def change_sale_channel_from_pos(self, order_id, new_sale_channel_id, supervisor_pin, pos_session_id=False):
        order = self.browse(order_id)
        if not order.exists():
            raise UserError(_("The selected order no longer exists."))

        order._check_paid_order_change_allowed(pos_session_id=pos_session_id)
        new_sale_channel = self.env["pos.sale.channel"].browse(new_sale_channel_id)
        if not new_sale_channel.exists():
            raise UserError(_("The selected sales channel does not exist."))
        if new_sale_channel == order.sale_channel_id:
            raise UserError(_("The new sales channel must be different from the current one."))
        if new_sale_channel not in order._get_changeable_sale_channels():
            raise UserError(_("The selected sales channel is not allowed for this POS order."))

        pin_record = self.env["pos.supervisor.pin"].sudo().get_company_pin(order.company_id)
        used_pin_masked = pin_record.sudo().consume_pin(supervisor_pin, self.env.user)

        old_sale_channel = order.sale_channel_id
        order.write({"sale_channel_id": new_sale_channel.id})
        if "sale_channel_id" in order.lines._fields:
            order.lines.write({"sale_channel_id": new_sale_channel.id})
        order.write(
            {
                "last_payment_method_change_at": fields.Datetime.now(),
                "last_payment_method_change_by_id": self.env.user.id,
            }
        )
        self._create_revision_log(
            {
                "change_type": "sale_channel",
                "change_origin": "pos_frontend",
                "old_sale_channel_id": old_sale_channel.id if old_sale_channel else False,
                "new_sale_channel_id": new_sale_channel.id,
                "change_reason": _("POS frontend correction approved with supervisor PIN."),
                "old_snapshot": old_sale_channel.display_name or _("Unassigned"),
                "new_snapshot": new_sale_channel.display_name,
                "used_pin_masked": used_pin_masked,
            }
        )
        self.env["pos.sale.channel.change.log"].sudo().create(
            {
                "order_id": order.id,
                "old_sale_channel_id": old_sale_channel.id if old_sale_channel else False,
                "new_sale_channel_id": new_sale_channel.id,
                "executed_by_id": self.env.user.id,
                "used_pin_masked": used_pin_masked,
            }
        )

        if hasattr(order, "message_post"):
            order.message_post(
                body=_("Sales channel changed from %(old)s to %(new)s by %(user)s.")
                % {
                    "old": old_sale_channel.display_name or _("Unassigned"),
                    "new": new_sale_channel.display_name,
                    "user": self.env.user.display_name,
                }
            )

        return {
            "success": True,
            "order": order._get_sale_channel_ui_data(),
        }

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="Sales Channel",
        index=True,
        ondelete="set null",
    )
    online_check_required = fields.Boolean(
        string="Online Checker Required",
        copy=False,
        default=False,
    )
    online_check_status = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("checked", "Checked"),
            ("overridden", "Overridden"),
        ],
        string="Online Check Status",
        copy=False,
        default="not_required",
    )
    online_check_note = fields.Text(
        string="Online Check Note",
        copy=False,
    )
    online_check_completed_at = fields.Datetime(
        string="Online Check Completed At",
        copy=False,
    )
    online_check_completed_by_id = fields.Many2one(
        "res.users",
        string="Online Check Completed By",
        copy=False,
    )
    online_check_override_reason = fields.Text(
        string="Override Reason",
        copy=False,
    )
    online_check_override_at = fields.Datetime(
        string="Override At",
        copy=False,
    )
    online_check_override_by_id = fields.Many2one(
        "res.users",
        string="Override By",
        copy=False,
    )
    online_check_ordered_qty_total = fields.Float(
        string="Ordered Qty to Check",
        compute="_compute_online_check_summary",
    )
    online_check_checked_qty_total = fields.Float(
        string="Checked Qty",
        compute="_compute_online_check_summary",
    )
    online_check_total_line_count = fields.Integer(
        string="Total Lines to Check",
        compute="_compute_online_check_summary",
    )
    online_check_checked_line_count = fields.Integer(
        string="Checked Lines",
        compute="_compute_online_check_summary",
    )
    online_check_progress_display = fields.Char(
        string="Online Check Progress",
        compute="_compute_online_check_summary",
    )

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        orders._sync_online_check_status()
        return orders

    def write(self, vals):
        result = super().write(vals)
        if self.env.context.get("skip_online_checker_sync"):
            return result
        if {"sale_channel_id", "session_id", "config_id", "state"} & set(vals):
            self._sync_online_check_status()
        return result

    @api.model
    def _get_default_sale_channel_id(self, session_id):
        if not session_id:
            return False
        session = self.env["pos.session"].browse(session_id)
        if not session.exists():
            return False
        channel = self.env["pos.sale.channel"].search(
            [
                ("active", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", session.company_id.id),
            ],
            order="sequence, id",
            limit=1,
        )
        return channel.id

    @api.model
    def _order_fields(self, ui_order):
        values = super()._order_fields(ui_order)
        data = ui_order.get("data", ui_order)
        values["sale_channel_id"] = data.get("sale_channel_id") or self._get_default_sale_channel_id(
            data.get("pos_session_id")
        )
        values["online_check_note"] = data.get("online_check_note") or False
        return values

    def action_pos_order_paid(self):
        result = super().action_pos_order_paid()
        self._sync_online_check_status()
        return result

    def _export_for_ui(self, order):
        values = super()._export_for_ui(order)
        values.update(
            {
                "sale_channel_id": order.sale_channel_id.id,
                "online_check_required": order.online_check_required,
                "online_check_status": order.online_check_status,
                "online_check_note": order.online_check_note or "",
                "online_check_progress_display": order.online_check_progress_display or "",
                "online_check_can_manage": order.env.user.has_group("point_of_sale.group_pos_manager"),
            }
        )
        return values

    @api.depends(
        "sale_channel_id",
        "config_id.online_checker_channel_ids",
        "lines.sale_channel_id",
        "lines.qty",
        "lines.online_check_qty",
    )
    def _compute_online_check_summary(self):
        for order in self:
            lines = order._get_online_checker_lines()
            ordered_qty_total = sum(max(line.qty or 0.0, 0.0) for line in lines)
            checked_qty_total = sum(min(max(line.online_check_qty or 0.0, 0.0), max(line.qty or 0.0, 0.0)) for line in lines)
            total_line_count = len(lines)
            checked_line_count = len(
                lines.filtered(
                    lambda line: max(line.qty or 0.0, 0.0) > 0.0
                    and min(max(line.online_check_qty or 0.0, 0.0), max(line.qty or 0.0, 0.0)) >= max(line.qty or 0.0, 0.0)
                )
            )
            order.online_check_ordered_qty_total = ordered_qty_total
            order.online_check_checked_qty_total = checked_qty_total
            order.online_check_total_line_count = total_line_count
            order.online_check_checked_line_count = checked_line_count
            order.online_check_progress_display = order._format_online_check_progress(
                checked_qty_total,
                ordered_qty_total,
                checked_line_count,
                total_line_count,
            )

    def _format_online_check_progress(self, checked_qty, ordered_qty, checked_lines, total_lines):
        return _("%(checked_qty)s/%(ordered_qty)s qty | %(checked_lines)s/%(total_lines)s lines") % {
            "checked_qty": self._format_online_check_number(checked_qty),
            "ordered_qty": self._format_online_check_number(ordered_qty),
            "checked_lines": checked_lines,
            "total_lines": total_lines,
        }

    def _format_online_check_number(self, number):
        rounded = round(number or 0.0, 6)
        if abs(rounded - int(rounded)) < 0.000001:
            return str(int(rounded))
        return ("%0.2f" % rounded).rstrip("0").rstrip(".")

    def _get_online_checker_channel_ids(self):
        self.ensure_one()
        return set(self.config_id.online_checker_channel_ids.ids)

    def _get_online_checker_lines(self):
        self.ensure_one()
        checker_channel_ids = self._get_online_checker_channel_ids()
        if not checker_channel_ids:
            return self.env["pos.order.line"]
        return self.lines.filtered(
            lambda line: max(line.qty or 0.0, 0.0) > 0.0
            and ((line.sale_channel_id or self.sale_channel_id).id in checker_channel_ids)
        )

    def _has_online_check_progress(self):
        self.ensure_one()
        return any(line.online_check_qty > 0.0 for line in self._get_online_checker_lines())

    def _all_online_checker_lines_fully_matched(self):
        self.ensure_one()
        lines = self._get_online_checker_lines()
        return bool(lines) and all(
            min(max(line.online_check_qty or 0.0, 0.0), max(line.qty or 0.0, 0.0)) >= max(line.qty or 0.0, 0.0)
            for line in lines
        )

    def _sync_online_check_status(self):
        for order in self:
            checker_lines = order._get_online_checker_lines()
            required = bool(checker_lines)
            values = {"online_check_required": required}
            if not required:
                values.update(
                    {
                        "online_check_status": "not_required",
                        "online_check_completed_at": False,
                        "online_check_completed_by_id": False,
                        "online_check_override_reason": False,
                        "online_check_override_at": False,
                        "online_check_override_by_id": False,
                    }
                )
            elif order.online_check_status not in ("checked", "overridden"):
                values["online_check_status"] = "in_progress" if order._has_online_check_progress() else "pending"

            order.with_context(skip_online_checker_sync=True).write(values)

    def _check_online_checker_required(self):
        self.ensure_one()
        if not self.online_check_required:
            raise UserError(_("This order does not require the online order checker."))

    def _check_online_checker_manager_access(self):
        if not self.env.user.has_group("point_of_sale.group_pos_manager"):
            raise UserError(_("Only a POS Manager can perform this action."))

    def _check_online_checker_editable(self):
        self.ensure_one()
        if self.online_check_status in ("checked", "overridden"):
            raise UserError(_("This checker is locked. Reopen it first to make changes."))

    def _apply_online_checker_payload(self, payload=None):
        self.ensure_one()
        payload = payload or {}
        if "note" in payload:
            self.with_context(skip_online_checker_sync=True).write({"online_check_note": payload.get("note") or False})

        checker_lines = {line.id: line for line in self._get_online_checker_lines()}
        for line_update in payload.get("line_updates", []):
            line_id = line_update.get("line_id")
            line = checker_lines.get(line_id)
            if not line:
                raise UserError(_("One of the selected lines is not part of the online checker scope."))

            checked_qty = float(line_update.get("checked_qty") or 0.0)
            ordered_qty = max(line.qty or 0.0, 0.0)
            if checked_qty < 0.0 or checked_qty - ordered_qty > 0.000001:
                raise UserError(
                    _("Checked quantity for %(product)s must be between 0 and %(qty)s.")
                    % {
                        "product": line.full_product_name or line.product_id.display_name,
                        "qty": self._format_online_check_number(ordered_qty),
                    }
                )
            line.write({"online_check_qty": checked_qty})

        self._sync_online_check_status()

    def _get_online_checker_payload_dict(self):
        self.ensure_one()
        checker_lines = self._get_online_checker_lines()
        return {
            "order_id": self.id,
            "order_name": self.pos_reference or self.name,
            "sale_channel_name": self.sale_channel_id.name or "",
            "partner_name": self.partner_id.name or "",
            "online_check_required": self.online_check_required,
            "online_check_status": self.online_check_status,
            "online_check_note": self.online_check_note or "",
            "online_check_progress_display": self.online_check_progress_display or "",
            "online_check_ordered_qty_total": self.online_check_ordered_qty_total,
            "online_check_checked_qty_total": self.online_check_checked_qty_total,
            "online_check_total_line_count": self.online_check_total_line_count,
            "online_check_checked_line_count": self.online_check_checked_line_count,
            "online_check_can_manage": self.env.user.has_group("point_of_sale.group_pos_manager"),
            "online_check_override_reason": self.online_check_override_reason or "",
            "lines": [
                {
                    "line_id": line.id,
                    "product_name": line.full_product_name or line.product_id.display_name,
                    "sale_channel_name": (line.sale_channel_id or self.sale_channel_id).name or "",
                    "ordered_qty": max(line.qty or 0.0, 0.0),
                    "checked_qty": min(max(line.online_check_qty or 0.0, 0.0), max(line.qty or 0.0, 0.0)),
                    "remaining_qty": max(line.qty or 0.0, 0.0)
                    - min(max(line.online_check_qty or 0.0, 0.0), max(line.qty or 0.0, 0.0)),
                    "status": line.online_check_status,
                }
                for line in checker_lines
            ],
        }

    @api.model
    def read_online_checker_receipt_data(self, order_ids):
        orders = self.browse(order_ids)
        return [order._get_online_checker_payload_dict() for order in orders]

    def get_online_checker_payload(self):
        self.ensure_one()
        self._check_online_checker_required()
        return self._get_online_checker_payload_dict()

    def save_online_checker_progress(self, payload=None):
        self.ensure_one()
        self._check_online_checker_required()
        self._check_online_checker_editable()
        self._apply_online_checker_payload(payload)
        return self._get_online_checker_payload_dict()

    def complete_online_checker(self, payload=None):
        self.ensure_one()
        self._check_online_checker_required()
        self._check_online_checker_editable()
        self._apply_online_checker_payload(payload)
        if not self._all_online_checker_lines_fully_matched():
            raise UserError(_("All online checker quantities must match the order before completion."))

        self.with_context(skip_online_checker_sync=True).write(
            {
                "online_check_status": "checked",
                "online_check_completed_at": fields.Datetime.now(),
                "online_check_completed_by_id": self.env.user.id,
                "online_check_override_reason": False,
                "online_check_override_at": False,
                "online_check_override_by_id": False,
            }
        )
        return self._get_online_checker_payload_dict()

    def override_online_checker(self, reason, payload=None):
        self.ensure_one()
        self._check_online_checker_required()
        self._check_online_checker_editable()
        self._check_online_checker_manager_access()
        if not (reason or "").strip():
            raise UserError(_("Override reason is required."))

        self._apply_online_checker_payload(payload)
        self.with_context(skip_online_checker_sync=True).write(
            {
                "online_check_status": "overridden",
                "online_check_completed_at": False,
                "online_check_completed_by_id": False,
                "online_check_override_reason": reason.strip(),
                "online_check_override_at": fields.Datetime.now(),
                "online_check_override_by_id": self.env.user.id,
            }
        )
        return self._get_online_checker_payload_dict()

    def reopen_online_checker(self):
        self.ensure_one()
        self._check_online_checker_required()
        self._check_online_checker_manager_access()
        if self.online_check_status not in ("checked", "overridden"):
            raise UserError(_("Only completed checkers can be reopened."))

        self.with_context(skip_online_checker_sync=True).write(
            {
                "online_check_completed_at": False,
                "online_check_completed_by_id": False,
                "online_check_override_reason": False,
                "online_check_override_at": False,
                "online_check_override_by_id": False,
            }
        )
        self._sync_online_check_status()
        return self._get_online_checker_payload_dict()

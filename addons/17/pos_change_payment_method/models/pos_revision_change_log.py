from odoo import api, fields, models


class PosRevisionChangeLog(models.Model):
    _name = "pos.revision.change.log"
    _description = "POS Revision Change Log"
    _order = "change_datetime desc, id desc"

    order_id = fields.Many2one(
        "pos.order",
        string="POS Order",
        required=True,
        index=True,
        ondelete="cascade",
    )
    session_id = fields.Many2one(
        related="order_id.session_id",
        store=True,
        readonly=True,
    )
    session_state = fields.Selection(
        related="order_id.session_id.state",
        string="Session State",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="order_id.company_id",
        store=True,
        readonly=True,
    )
    original_cashier_id = fields.Many2one(
        related="order_id.user_id",
        string="Original Cashier",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )
    change_type = fields.Selection(
        [
            ("payment_method", "Payment Method"),
            ("sale_channel", "Sales Channel"),
            ("order_void", "Order Void"),
        ],
        string="Revision Type",
        required=True,
        readonly=True,
    )
    change_origin = fields.Selection(
        [
            ("pos_frontend", "POS Frontend"),
            ("backend_finance", "Backend Finance"),
            ("migration", "Migration"),
        ],
        string="Origin",
        required=True,
        readonly=True,
        default="pos_frontend",
    )
    old_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Old Payment Method",
        readonly=True,
    )
    new_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="New Payment Method",
        readonly=True,
    )
    old_sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="Old Sales Channel",
        readonly=True,
    )
    new_sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="New Sales Channel",
        readonly=True,
    )
    related_order_id = fields.Many2one(
        "pos.order",
        string="Related POS Order",
        readonly=True,
    )
    old_value_display = fields.Char(
        string="Old Value",
        compute="_compute_value_display",
        store=True,
    )
    new_value_display = fields.Char(
        string="New Value",
        compute="_compute_value_display",
        store=True,
    )
    payment_amount = fields.Monetary(
        string="Payment Amount",
        readonly=True,
    )
    change_reason = fields.Text(
        string="Reason",
        readonly=True,
    )
    old_snapshot = fields.Text(
        string="Old Snapshot",
        readonly=True,
    )
    new_snapshot = fields.Text(
        string="New Snapshot",
        readonly=True,
    )
    change_datetime = fields.Datetime(
        string="Changed At",
        required=True,
        readonly=True,
        default=fields.Datetime.now,
    )
    executed_by_id = fields.Many2one(
        "res.users",
        string="Executed By",
        required=True,
        readonly=True,
    )
    used_pin_masked = fields.Char(
        string="Used PIN (Masked)",
        readonly=True,
    )
    policy_status = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("within_window", "Within Window"),
            ("override", "Override Used"),
        ],
        string="Security Policy",
        readonly=True,
        default="not_applicable",
    )
    policy_note = fields.Text(
        string="Security Policy Detail",
        readonly=True,
    )

    @api.depends(
        "change_type",
        "old_payment_method_id",
        "new_payment_method_id",
        "old_sale_channel_id",
        "new_sale_channel_id",
    )
    def _compute_value_display(self):
        for record in self:
            if record.change_type == "payment_method":
                record.old_value_display = record.old_payment_method_id.display_name or ""
                record.new_value_display = record.new_payment_method_id.display_name or ""
            elif record.change_type == "sale_channel":
                record.old_value_display = record.old_sale_channel_id.display_name or ""
                record.new_value_display = record.new_sale_channel_id.display_name or ""
            else:
                record.old_value_display = record.order_id.display_name or ""
                record.new_value_display = record.related_order_id.display_name or ""

    @api.model
    def cleanup_legacy_revision_menu_entries(self):
        self._ensure_revision_log_access_rules()
        self._ensure_wizard_access_rules()
        self._backfill_legacy_revision_logs()
        return True

    @api.model
    def _ensure_revision_log_access_rules(self):
        model = self.env["ir.model"].sudo().search([("model", "=", "pos.revision.change.log")], limit=1)
        if not model:
            return

        access_model = self.env["ir.model.access"].sudo()
        access_specs = [
            (
                "pos.revision.change.log cashier supervisor",
                "bakery_user_roles.group_bakery_cashier_supervisor",
            ),
            (
                "pos.revision.change.log finance",
                "bakery_user_roles.group_bakery_finance",
            ),
        ]
        for name, group_xmlid in access_specs:
            group = self.env.ref(group_xmlid, raise_if_not_found=False)
            if not group:
                continue

            access = access_model.search(
                [
                    ("name", "=", name),
                    ("model_id", "=", model.id),
                    ("group_id", "=", group.id),
                ],
                limit=1,
            )
            values = {
                "name": name,
                "model_id": model.id,
                "group_id": group.id,
                "perm_read": True,
                "perm_write": False,
                "perm_create": False,
                "perm_unlink": False,
            }
            if access:
                access.write(values)
            else:
                access_model.create(values)

    @api.model
    def _ensure_wizard_access_rules(self):
        access_model = self.env["ir.model.access"].sudo()
        finance_group = self.env.ref("bakery_user_roles.group_bakery_finance", raise_if_not_found=False)
        if not finance_group:
            return

        wizard_specs = [
            (
                "pos.backend.payment.revision.wizard",
                "pos.backend.payment.revision.wizard finance",
            ),
            (
                "pos.backend.payment.revision.wizard.line",
                "pos.backend.payment.revision.wizard line finance",
            ),
            (
                "pos.backend.sale.channel.revision.wizard",
                "pos.backend.sale.channel.revision.wizard finance",
            ),
            (
                "pos.backend.void.order.wizard",
                "pos.backend.void.order.wizard finance",
            ),
        ]

        for model_name, access_name in wizard_specs:
            model = self.env["ir.model"].sudo().search([("model", "=", model_name)], limit=1)
            if not model:
                continue

            access = access_model.search(
                [
                    ("name", "=", access_name),
                    ("model_id", "=", model.id),
                    ("group_id", "=", finance_group.id),
                ],
                limit=1,
            )
            values = {
                "name": access_name,
                "model_id": model.id,
                "group_id": finance_group.id,
                "perm_read": True,
                "perm_write": True,
                "perm_create": True,
                "perm_unlink": True,
            }
            if access:
                access.write(values)
            else:
                access_model.create(values)

    @api.model
    def _backfill_legacy_revision_logs(self):
        self._backfill_payment_method_logs()
        self._backfill_sale_channel_logs()

    @api.model
    def _backfill_payment_method_logs(self):
        legacy_logs = self.env["pos.payment.method.change.log"].sudo().search([])
        for legacy_log in legacy_logs:
            exists = self.sudo().search_count(
                [
                    ("order_id", "=", legacy_log.order_id.id),
                    ("change_type", "=", "payment_method"),
                    ("change_datetime", "=", legacy_log.change_datetime),
                    ("old_payment_method_id", "=", legacy_log.old_payment_method_id.id),
                    ("new_payment_method_id", "=", legacy_log.new_payment_method_id.id),
                    ("executed_by_id", "=", legacy_log.executed_by_id.id),
                ]
            )
            if exists:
                continue

            self.sudo().create(
                {
                    "order_id": legacy_log.order_id.id,
                    "change_type": "payment_method",
                    "change_origin": "migration",
                    "old_payment_method_id": legacy_log.old_payment_method_id.id,
                    "new_payment_method_id": legacy_log.new_payment_method_id.id,
                    "payment_amount": legacy_log.payment_amount,
                    "old_snapshot": "%s: %s"
                    % (
                        legacy_log.old_payment_method_id.display_name,
                        legacy_log.payment_amount,
                    ),
                    "new_snapshot": "%s: %s"
                    % (
                        legacy_log.new_payment_method_id.display_name,
                        legacy_log.payment_amount,
                    ),
                    "change_datetime": legacy_log.change_datetime,
                    "executed_by_id": legacy_log.executed_by_id.id,
                    "used_pin_masked": legacy_log.used_pin_masked,
                }
            )

    @api.model
    def _backfill_sale_channel_logs(self):
        legacy_logs = self.env["pos.sale.channel.change.log"].sudo().search([])
        for legacy_log in legacy_logs:
            exists = self.sudo().search_count(
                [
                    ("order_id", "=", legacy_log.order_id.id),
                    ("change_type", "=", "sale_channel"),
                    ("change_datetime", "=", legacy_log.change_datetime),
                    ("old_sale_channel_id", "=", legacy_log.old_sale_channel_id.id),
                    ("new_sale_channel_id", "=", legacy_log.new_sale_channel_id.id),
                    ("executed_by_id", "=", legacy_log.executed_by_id.id),
                ]
            )
            if exists:
                continue

            self.sudo().create(
                {
                    "order_id": legacy_log.order_id.id,
                    "change_type": "sale_channel",
                    "change_origin": "migration",
                    "old_sale_channel_id": legacy_log.old_sale_channel_id.id,
                    "new_sale_channel_id": legacy_log.new_sale_channel_id.id,
                    "old_snapshot": legacy_log.old_sale_channel_id.display_name or "",
                    "new_snapshot": legacy_log.new_sale_channel_id.display_name or "",
                    "change_datetime": legacy_log.change_datetime,
                    "executed_by_id": legacy_log.executed_by_id.id,
                    "used_pin_masked": legacy_log.used_pin_masked,
                }
            )

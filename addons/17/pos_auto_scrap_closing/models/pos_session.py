from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_is_zero


class PosSession(models.Model):
    _inherit = "pos.session"

    auto_scrap_currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Accounting Currency",
        readonly=True,
    )
    auto_scrap_ids = fields.One2many(
        "stock.scrap",
        "pos_session_id",
        string="Auto Scraps",
        readonly=True,
    )
    auto_scrap_count = fields.Integer(
        string="Auto Scrap Count",
        compute="_compute_auto_scrap_summary",
    )
    auto_scrap_qty_total = fields.Float(
        string="Auto Scrap Quantity",
        compute="_compute_auto_scrap_summary",
    )
    auto_scrap_value_total = fields.Monetary(
        string="Auto Scrap Loss Value",
        compute="_compute_auto_scrap_summary",
        currency_field="auto_scrap_currency_id",
    )
    auto_scrap_projected_qty_total = fields.Float(
        string="Projected Auto Scrap Quantity",
        compute="_compute_auto_scrap_projection",
    )
    auto_scrap_projected_value_total = fields.Monetary(
        string="Projected Auto Scrap Loss",
        compute="_compute_auto_scrap_projection",
        currency_field="auto_scrap_currency_id",
    )
    auto_scrap_requires_approval = fields.Boolean(
        string="Auto Scrap Approval Required",
        compute="_compute_auto_scrap_projection",
    )
    auto_scrap_approval_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("pending", "Pending Approval"),
            ("approved", "Approved"),
            ("stale", "Reapproval Needed"),
        ],
        string="Auto Scrap Approval Status",
        compute="_compute_auto_scrap_approval_state",
    )
    auto_scrap_approved_by_id = fields.Many2one(
        "res.users",
        string="Approved By",
        readonly=True,
        copy=False,
    )
    auto_scrap_approved_at = fields.Datetime(
        string="Approved At",
        readonly=True,
        copy=False,
    )
    auto_scrap_approval_reason = fields.Text(
        string="Approval Reason",
        readonly=True,
        copy=False,
    )
    auto_scrap_approval_estimated_value = fields.Monetary(
        string="Approved Projected Loss",
        currency_field="auto_scrap_currency_id",
        readonly=True,
        copy=False,
    )

    def action_pos_session_close(
        self,
        balancing_account=False,
        amount_to_balance=0,
        bank_payment_method_diffs=None,
    ):
        self.ensure_one()
        approval_block_message = self._get_auto_scrap_approval_block_message()
        if approval_block_message:
            raise UserError(approval_block_message)

        result = super().action_pos_session_close(
            balancing_account=balancing_account,
            amount_to_balance=amount_to_balance,
            bank_payment_method_diffs=bank_payment_method_diffs,
        )
        if result is True:
            scraps = self._auto_scrap_unsold_products()
            self._message_auto_scrap_limit_exceeded(scraps)
        return result

    def close_session_from_ui(self, bank_payment_method_diff_pairs=None):
        self.ensure_one()
        approval_block_message = self._get_auto_scrap_approval_block_message(from_ui=True)
        if approval_block_message:
            return {
                "successful": False,
                "type": "alert",
                "title": _("Manager approval required"),
                "message": approval_block_message,
                "redirect": False,
            }
        return super().close_session_from_ui(
            bank_payment_method_diff_pairs=bank_payment_method_diff_pairs
        )

    @api.depends(
        "auto_scrap_ids.state",
        "auto_scrap_ids.scrap_qty",
        "auto_scrap_ids.loss_value",
    )
    def _compute_auto_scrap_summary(self):
        for session in self:
            done_scraps = session.auto_scrap_ids.filtered(lambda scrap: scrap.state == "done")
            session.auto_scrap_count = len(done_scraps)
            session.auto_scrap_qty_total = sum(done_scraps.mapped("scrap_qty"))
            session.auto_scrap_value_total = sum(done_scraps.mapped("loss_value"))

    def _compute_auto_scrap_projection(self):
        for session in self:
            preview_data = session._get_auto_scrap_preview_data()
            session.auto_scrap_projected_qty_total = sum(
                candidate["scrap_qty"] for candidate in preview_data["candidates"]
            )
            session.auto_scrap_projected_value_total = preview_data["total_estimated_value"]
            session.auto_scrap_requires_approval = preview_data["requires_manager_approval"]

    def _compute_auto_scrap_approval_state(self):
        for session in self:
            preview_data = session._get_auto_scrap_preview_data()
            if session.state == "closed" and session.auto_scrap_approved_by_id:
                session.auto_scrap_approval_state = "approved"
            elif not preview_data["requires_manager_approval"]:
                session.auto_scrap_approval_state = "not_required"
            elif session._is_auto_scrap_approval_valid(preview_data):
                session.auto_scrap_approval_state = "approved"
            elif session.auto_scrap_approved_by_id:
                session.auto_scrap_approval_state = "stale"
            else:
                session.auto_scrap_approval_state = "pending"

    def _get_auto_scrap_origin(self):
        self.ensure_one()
        return _("%(session)s - POS closing", session=self.name)

    def _get_auto_scrap_source_location(self):
        self.ensure_one()
        return self.config_id.picking_type_id.default_location_src_id

    def _get_auto_scrap_candidates(self, projected=False):
        self.ensure_one()
        if not self.config_id.auto_scrap_unsold_products:
            return []

        source_location = self._get_auto_scrap_source_location()
        if not source_location:
            return []

        quant_domain = [
            ("company_id", "=", self.company_id.id),
            ("location_id", "child_of", source_location.id),
            ("location_id.usage", "=", "internal"),
            ("product_id.available_in_pos", "=", True),
            ("product_id.type", "=", "product"),
            ("product_id.product_tmpl_id.auto_scrap_on_pos_closing", "=", True),
            ("quantity", ">", 0),
        ]
        quants = (
            self.env["stock.quant"]
            .sudo()
            .with_company(self.company_id)
            .search(quant_domain, order="location_id, product_id, lot_id, package_id, owner_id, id")
        )

        candidates = []
        for quant in quants:
            available_qty = quant.quantity - quant.reserved_quantity
            if available_qty < 0 or float_is_zero(
                available_qty, precision_rounding=quant.product_id.uom_id.rounding
            ):
                continue

            unit_cost = quant.product_id.with_company(self.company_id).standard_price
            candidates.append(
                {
                    "product_id": quant.product_id.id,
                    "product_uom_id": quant.product_id.uom_id.id,
                    "location_id": quant.location_id.id,
                    "lot_id": quant.lot_id.id,
                    "package_id": quant.package_id.id,
                    "owner_id": quant.owner_id.id,
                    "scrap_qty": available_qty,
                    "estimated_value": available_qty * unit_cost,
                }
            )

        if projected and self._should_project_auto_scrap_preview():
            return self._project_auto_scrap_candidates(candidates, source_location)
        return candidates

    def _should_project_auto_scrap_preview(self):
        self.ensure_one()
        return self.update_stock_at_closing and self.state != "closed"

    def _project_auto_scrap_candidates(self, quant_candidates, source_location):
        self.ensure_one()
        available_qty_by_product = defaultdict(float)
        sold_qty_by_product = defaultdict(float)
        for candidate in quant_candidates:
            available_qty_by_product[candidate["product_id"]] += candidate["scrap_qty"]

        flagged_lines = self._get_closed_orders().mapped("lines").filtered(
            lambda line: (
                line.product_id.available_in_pos
                and line.product_id.type == "product"
                and line.product_id.product_tmpl_id.auto_scrap_on_pos_closing
            )
        )
        for line in flagged_lines:
            if float_is_zero(line.qty, precision_rounding=line.product_uom_id.rounding):
                continue
            sold_qty_by_product[line.product_id.id] += line.qty

        candidates = []
        products = self.env["product.product"].browse(
            list(available_qty_by_product.keys())
        ).sorted(key=lambda product: product.display_name)
        for product in products:
            projected_qty = available_qty_by_product[product.id] - sold_qty_by_product[product.id]
            if projected_qty < 0 or float_is_zero(
                projected_qty, precision_rounding=product.uom_id.rounding
            ):
                continue

            unit_cost = product.with_company(self.company_id).standard_price
            candidates.append(
                {
                    "product_id": product.id,
                    "product_uom_id": product.uom_id.id,
                    "location_id": source_location.id,
                    "lot_id": False,
                    "package_id": False,
                    "owner_id": False,
                    "scrap_qty": projected_qty,
                    "estimated_value": projected_qty * unit_cost,
                }
            )
        return candidates

    def _get_auto_scrap_preview_data(self):
        self.ensure_one()
        is_estimated = self._should_project_auto_scrap_preview()
        candidates = self._get_auto_scrap_candidates(projected=is_estimated)
        total_estimated_value = sum(candidate["estimated_value"] for candidate in candidates)
        requires_manager_approval = self._requires_manager_auto_scrap_approval(
            total_estimated_value
        )
        approval_valid = self._is_auto_scrap_approval_valid_for_amount(
            total_estimated_value, requires_manager_approval
        )

        note_parts = []
        if is_estimated:
            note_parts.append(
                _(
                    "Preview ini masih estimasi karena stok POS baru dikurangi saat session ditutup."
                )
            )
        if requires_manager_approval:
            note_parts.append(
                _(
                    "Estimasi loss auto scrap %(value).2f %(currency)s melebihi batas %(limit).2f %(currency)s dan harus ditutup oleh POS Manager.",
                    value=total_estimated_value,
                    limit=self.config_id.auto_scrap_loss_limit,
                    currency=self.auto_scrap_currency_id.name,
                )
            )
        if requires_manager_approval and approval_valid and self.auto_scrap_approved_by_id:
            note_parts.append(
                _(
                    "Approval sudah direkam oleh %(user)s pada %(date)s untuk estimasi loss %(value).2f %(currency)s.",
                    user=self.auto_scrap_approved_by_id.display_name,
                    date=fields.Datetime.to_string(self.auto_scrap_approved_at),
                    value=self.auto_scrap_approval_estimated_value,
                    currency=self.auto_scrap_currency_id.name,
                )
            )
        elif requires_manager_approval and self.auto_scrap_approved_by_id and not approval_valid:
            note_parts.append(
                _(
                    "Approval sebelumnya perlu diperbarui karena estimasi loss sekarang lebih besar dari approval terakhir."
                )
            )
        return {
            "candidates": candidates,
            "is_estimated": is_estimated,
            "requires_manager_approval": requires_manager_approval,
            "note": "\n".join(note_parts),
            "total_estimated_value": total_estimated_value,
            "approval_valid": approval_valid,
        }

    def _requires_manager_auto_scrap_approval(self, estimated_loss_value):
        self.ensure_one()
        loss_limit = self.config_id.auto_scrap_loss_limit
        if not self.config_id.auto_scrap_require_manager_approval or not loss_limit:
            return False
        return self.auto_scrap_currency_id.compare_amounts(estimated_loss_value, loss_limit) > 0

    def _is_auto_scrap_approval_valid_for_amount(
        self, estimated_loss_value, requires_manager_approval
    ):
        self.ensure_one()
        if not self.auto_scrap_approved_by_id or not self.auto_scrap_approved_at:
            return False
        if not self.auto_scrap_approval_reason:
            return False
        if self.state == "closed":
            return True
        if not requires_manager_approval:
            return True
        if not self.auto_scrap_approval_estimated_value:
            return False
        return (
            self.auto_scrap_currency_id.compare_amounts(
                self.auto_scrap_approval_estimated_value, estimated_loss_value
            )
            >= 0
        )

    def _is_auto_scrap_approval_valid(self, preview_data=None):
        self.ensure_one()
        preview_data = preview_data or self._get_auto_scrap_preview_data()
        return self._is_auto_scrap_approval_valid_for_amount(
            preview_data["total_estimated_value"],
            preview_data["requires_manager_approval"],
        )

    def _get_auto_scrap_approval_block_message(self, from_ui=False):
        self.ensure_one()
        preview_data = self._get_auto_scrap_preview_data()
        if not preview_data["requires_manager_approval"]:
            return False
        if preview_data["approval_valid"]:
            return False
        message = _(
            "Projected auto scrap loss %(value).2f %(currency)s exceeds the allowed threshold of %(limit).2f %(currency)s.",
            value=preview_data["total_estimated_value"],
            limit=self.config_id.auto_scrap_loss_limit,
            currency=self.auto_scrap_currency_id.name,
        )
        if self.user_has_groups("point_of_sale.group_pos_manager"):
            if from_ui:
                return _(
                    "%(message)s Record the approval reason on the POS session form before closing from the POS UI.",
                    message=message,
                )
            return _(
                "%(message)s Use the Approve Auto Scrap action on the POS session before closing.",
                message=message,
            )
        if self.auto_scrap_approved_by_id:
            return _(
                "%(message)s The previous approval is no longer sufficient and must be refreshed by a POS Manager.",
                message=message,
            )
        return _(
            "%(message)s A POS Manager must approve this session before it can be closed.",
            message=message,
        )

    def _message_auto_scrap_limit_exceeded(self, scraps):
        self.ensure_one()
        if not scraps or not self.config_id.auto_scrap_require_manager_approval:
            return

        loss_limit = self.config_id.auto_scrap_loss_limit
        if not loss_limit:
            return

        total_loss_value = sum(scraps.mapped("loss_value"))
        if self.auto_scrap_currency_id.compare_amounts(total_loss_value, loss_limit) <= 0:
            return

        self.message_post(
            body=_(
                "Auto scrap loss %(value).2f %(currency)s exceeded the configured threshold of %(limit).2f %(currency)s. Session closed by %(user)s.",
                value=total_loss_value,
                limit=loss_limit,
                currency=self.auto_scrap_currency_id.name,
                user=self.env.user.display_name,
            )
        )

    def action_open_auto_scrap_approval_wizard(self):
        self.ensure_one()
        if not self.user_has_groups("point_of_sale.group_pos_manager"):
            raise UserError(_("Only a POS Manager can approve auto scrap loss."))

        preview_data = self._get_auto_scrap_preview_data()
        if not preview_data["requires_manager_approval"]:
            raise UserError(_("The current projected auto scrap loss does not require approval."))

        wizard = self.env["pos.auto.scrap.approval.wizard"].create(
            {
                "session_id": self.id,
                "projected_loss_value": preview_data["total_estimated_value"],
                "loss_limit": self.config_id.auto_scrap_loss_limit,
                "reason": self.auto_scrap_approval_reason
                or _("Approved by manager due to acceptable daily wastage."),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Approve Auto Scrap"),
            "res_model": "pos.auto.scrap.approval.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    def _auto_scrap_unsold_products(self):
        self.ensure_one()
        candidates = self._get_auto_scrap_candidates()
        if not candidates:
            return self.env["stock.scrap"]
        scrap_model = self.env["stock.scrap"].sudo().with_company(self.company_id)
        scraps = self.env["stock.scrap"]
        origin = self._get_auto_scrap_origin()
        for candidate in candidates:
            scrap = scrap_model.create(
                {
                    "origin": origin,
                    "company_id": self.company_id.id,
                    "pos_session_id": self.id,
                    "product_id": candidate["product_id"],
                    "product_uom_id": candidate["product_uom_id"],
                    "scrap_qty": candidate["scrap_qty"],
                    "location_id": candidate["location_id"],
                    "lot_id": candidate["lot_id"],
                    "package_id": candidate["package_id"],
                    "owner_id": candidate["owner_id"],
                }
            )
            scrap.action_validate()
            scraps |= scrap

        if scraps:
            self.message_post(
                body=_(
                    "Auto scrap created %(count)s record(s) with total quantity %(qty)s.",
                    count=len(scraps),
                    qty=self.auto_scrap_qty_total or sum(scraps.mapped("scrap_qty")),
                )
            )
        return scraps

    def action_view_auto_scraps(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id("stock.action_stock_scrap")
        action["domain"] = [("id", "in", self.auto_scrap_ids.ids)]
        action["context"] = {
            **self.env.context,
            "default_pos_session_id": self.id,
            "search_default_groupby_product_id": 0,
        }
        return action

    def action_open_auto_scrap_preview(self):
        self.ensure_one()
        preview_data = self._get_auto_scrap_preview_data()
        wizard = self.env["pos.auto.scrap.preview.wizard"].create(
            {
                "session_id": self.id,
                "note": preview_data["note"],
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": candidate["product_id"],
                            "product_uom_id": candidate["product_uom_id"],
                            "location_id": candidate["location_id"],
                            "lot_id": candidate["lot_id"],
                            "scrap_qty": candidate["scrap_qty"],
                            "estimated_value": candidate["estimated_value"],
                        },
                    )
                    for candidate in preview_data["candidates"]
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Auto Scrap Preview"),
            "res_model": "pos.auto.scrap.preview.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

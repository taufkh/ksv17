import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosOrder(models.Model):
    _inherit = "pos.order"

    membership_claim_reward = fields.Boolean(copy=False)
    membership_claim_product_id = fields.Many2one("product.product", copy=False)
    membership_points_earned = fields.Integer(copy=False)
    membership_deposit_amount_used = fields.Monetary(
        currency_field="currency_id",
        copy=False,
        default=0.0,
    )
    membership_topup_amount = fields.Monetary(
        currency_field="currency_id",
        copy=False,
        default=0.0,
    )

    @api.model
    def _order_fields(self, ui_order):
        values = super()._order_fields(ui_order)
        data = ui_order.get("data", ui_order)
        values.update(
            {
                "membership_claim_reward": bool(data.get("membership_claim_reward")),
                "membership_claim_product_id": data.get("membership_claim_product_id") or False,
                "membership_points_earned": int(data.get("membership_points_earned_preview") or 0),
                "membership_deposit_amount_used": data.get("membership_deposit_amount_used") or 0.0,
                "membership_topup_amount": data.get("membership_topup_amount") or 0.0,
            }
        )
        return values

    def _export_for_ui(self, order):
        values = super()._export_for_ui(order)
        deposit_total = order.partner_id._get_membership_deposit_totals().get(order.partner_id.id, 0.0) if order.partner_id else 0.0
        point_total = order.partner_id._get_membership_point_totals().get(order.partner_id.id, 0) if order.partner_id else 0
        values.update(
            {
                "membership_claim_reward": order.membership_claim_reward,
                "membership_claim_product_id": order.membership_claim_product_id.id,
                "membership_points_earned": order.membership_points_earned,
                "membership_deposit_amount_used": order.membership_deposit_amount_used,
                "membership_topup_amount": order.membership_topup_amount,
                "membership_balance_after": deposit_total,
                "membership_points_total": point_total,
            }
        )
        return values

    @api.model
    def create_from_ui(self, orders, draft=False):
        results = super().create_from_ui(orders, draft=draft)
        if draft:
            return results
        for ui_order, result in zip(orders, results):
            order = self.browse(result["id"])
            order._sync_membership_from_ui_payload(ui_order)
        return results

    def _get_membership_topup_amount(self):
        self.ensure_one()
        topup_product = self.company_id.membership_topup_product_id
        if not topup_product:
            return 0.0
        return sum(
            self.lines.filtered(lambda line: line.product_id == topup_product).mapped("price_subtotal_incl")
        )

    def _get_membership_deposit_usage_amount(self):
        self.ensure_one()
        return sum(
            self.payment_ids.filtered(lambda payment: payment.payment_method_id.is_membership_deposit).mapped("amount")
        )

    def _get_membership_points_base_amount(self):
        self.ensure_one()
        topup_product = self.company_id.membership_topup_product_id
        reward_product = self.membership_claim_product_id
        eligible_lines = self.lines.filtered(
            lambda line: line.price_subtotal_incl > 0
            and line.qty > 0
            and line.product_id != topup_product
            and line.product_id != reward_product
        )
        return sum(eligible_lines.mapped("price_subtotal_incl"))

    def _calculate_membership_points(self):
        self.ensure_one()
        spend_amount = self.company_id.membership_point_spend_amount
        point_value = self.company_id.membership_point_value
        if not spend_amount or spend_amount <= 0 or point_value <= 0:
            return 0
        base_amount = self._get_membership_points_base_amount()
        if base_amount <= 0:
            return 0
        return int(math.floor(base_amount / spend_amount) * point_value)

    def _sync_membership_from_ui_payload(self, ui_order):
        self.ensure_one()
        partner = self.partner_id
        if not partner or not partner.is_custom_member:
            return

        deposit_usage = self._get_membership_deposit_usage_amount()
        topup_amount = self._get_membership_topup_amount()
        points_earned = self._calculate_membership_points()

        self.write(
            {
                "membership_deposit_amount_used": deposit_usage,
                "membership_topup_amount": topup_amount,
                "membership_points_earned": points_earned,
            }
        )

        reference = self.pos_reference or self.name

        if topup_amount and not self.env["membership.deposit.ledger"].search_count(
            [("pos_order_id", "=", self.id), ("source", "=", "topup"), ("direction", "=", "in")]
        ):
            partner.add_membership_deposit(
                topup_amount,
                source="topup",
                pos_order=self,
                reference=reference,
            )

        if deposit_usage and not self.env["membership.deposit.ledger"].search_count(
            [("pos_order_id", "=", self.id), ("source", "=", "usage"), ("direction", "=", "out")]
        ):
            partner.consume_membership_deposit(
                deposit_usage,
                source="usage",
                pos_order=self,
                reference=reference,
            )

        if points_earned and not self.env["membership.point.ledger"].search_count(
            [("pos_order_id", "=", self.id), ("source", "=", "pos_order"), ("direction", "=", "earned")]
        ):
            partner.add_membership_points(
                points_earned,
                source="pos_order",
                pos_order=self,
                reference=reference,
            )

        if self.membership_claim_reward and self.membership_claim_product_id:
            existing_claim = self.env["daily.claim.log"].search(
                [
                    ("partner_id", "=", partner.id),
                    ("company_id", "=", self.company_id.id),
                    ("date", "=", fields.Date.context_today(self)),
                    ("pos_order_id", "=", self.id),
                ],
                limit=1,
            )
            if not existing_claim:
                status = partner.get_daily_reward_status(company=self.company_id)
                if status["already_claimed"]:
                    raise UserError(_("Daily reward hanya dapat diklaim 1 kali per hari."))
                if self.membership_claim_product_id.id not in (status.get("reward_product_ids") or []):
                    raise UserError(_("The claimed reward product does not match today's configuration."))
                partner.consume_daily_reward(self.membership_claim_product_id, pos_order=self)

    @api.model
    def read_membership_receipt_data(self, order_ids):
        orders = self.browse(order_ids)
        result = []
        for order in orders:
            deposit_total = order.partner_id._get_membership_deposit_totals().get(order.partner_id.id, 0.0) if order.partner_id else 0.0
            point_total = order.partner_id._get_membership_point_totals().get(order.partner_id.id, 0) if order.partner_id else 0
            result.append(
                {
                    "membership_balance_after": deposit_total,
                    "membership_points_total": point_total,
                    "membership_points_earned": order.membership_points_earned,
                    "membership_deposit_amount_used": order.membership_deposit_amount_used,
                    "membership_topup_amount": order.membership_topup_amount,
                    "membership_claim_reward": order.membership_claim_reward,
                    "membership_claim_product_name": order.membership_claim_product_id.display_name,
                }
            )
        return result

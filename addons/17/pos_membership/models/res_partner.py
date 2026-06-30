from psycopg2 import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_custom_member = fields.Boolean(string="Custom Member", copy=False)
    custom_member_type = fields.Selection(
        [("free", "Free"), ("paid", "Paid")],
        string="Membership Type",
        default="free",
        copy=False,
    )
    custom_member_barcode = fields.Char(
        string="Membership Barcode",
        copy=False,
        index=True,
    )
    membership_portal_enabled = fields.Boolean(
        string="Portal Access Enabled",
        compute="_compute_membership_portal_enabled",
    )
    membership_last_checkin_date = fields.Date(copy=False)
    total_deposit_balance = fields.Monetary(
        string="Deposit Balance",
        compute="_compute_membership_balances",
        currency_field="currency_id",
    )
    total_points = fields.Integer(
        string="Total Points",
        compute="_compute_membership_balances",
    )

    _sql_constraints = [
        (
            "res_partner_custom_member_barcode_uniq",
            "unique(custom_member_barcode)",
            "Membership barcode must be unique.",
        ),
    ]

    @api.depends("user_ids.groups_id", "user_ids.active", "is_custom_member")
    def _compute_membership_portal_enabled(self):
        portal_group = self.env.ref("base.group_portal")
        for partner in self:
            partner.membership_portal_enabled = bool(
                partner.is_custom_member
                and partner.user_ids.filtered(lambda user: user.active and portal_group in user.groups_id)
            )

    @api.depends(
        "currency_id",
        "child_ids",
        "child_ids.currency_id",
    )
    def _compute_membership_balances(self):
        deposit_totals = self._get_membership_deposit_totals()
        point_totals = self._get_membership_point_totals()
        for partner in self:
            partner.total_deposit_balance = deposit_totals.get(partner.id, 0.0)
            partner.total_points = point_totals.get(partner.id, 0)

    def _get_membership_deposit_totals(self):
        totals = {}
        if not self.ids:
            return totals
        rows = self.env["membership.deposit.ledger"].read_group(
            [
                ("partner_id", "in", self.ids),
                ("state", "=", "posted"),
            ],
            ["partner_id", "amount:sum", "direction"],
            ["partner_id", "direction"],
            lazy=False,
        )
        for row in rows:
            partner_id = row["partner_id"][0]
            signed_amount = row["amount"]
            if row["direction"] == "out":
                signed_amount *= -1
            totals[partner_id] = totals.get(partner_id, 0.0) + signed_amount
        return totals

    def _get_membership_point_totals(self):
        totals = {}
        if not self.ids:
            return totals
        rows = self.env["membership.point.ledger"].read_group(
            [("partner_id", "in", self.ids)],
            ["partner_id", "points:sum", "direction"],
            ["partner_id", "direction"],
            lazy=False,
        )
        for row in rows:
            partner_id = row["partner_id"][0]
            signed_points = row["points"]
            if row["direction"] == "redeemed":
                signed_points *= -1
            totals[partner_id] = totals.get(partner_id, 0) + signed_points
        return totals

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._ensure_membership_barcode()
        return partners

    def write(self, vals):
        result = super().write(vals)
        if {"is_custom_member", "custom_member_barcode"} & set(vals):
            self._ensure_membership_barcode()
        return result

    def _ensure_membership_barcode(self):
        for partner in self.filtered(lambda p: p.is_custom_member and not p.custom_member_barcode):
            prefix = (partner.company_id.membership_barcode_prefix or "MBR").strip().upper()
            partner.custom_member_barcode = f"{prefix}-{partner.id:06d}"

    def _lock_membership_row(self):
        self.ensure_one()
        self.env.cr.execute("SELECT id FROM res_partner WHERE id = %s FOR UPDATE", [self.id])

    def add_membership_deposit(
        self,
        amount,
        source="adjustment",
        pos_order=False,
        pos_payment=False,
        reference=False,
        state="posted",
    ):
        self.ensure_one()
        if amount < 0:
            raise ValidationError(_("Deposit amount must be positive."))
        if not self.is_custom_member:
            raise UserError(_("Deposit balance can only be managed for custom members."))
        return self.env["membership.deposit.ledger"].create(
            {
                "partner_id": self.id,
                "company_id": self.company_id.id or self.env.company.id,
                "amount": amount,
                "direction": "in",
                "source": source,
                "pos_order_id": pos_order.id if pos_order else False,
                "pos_payment_id": pos_payment.id if pos_payment else False,
                "reference": reference or False,
                "state": state,
            }
        )

    def consume_membership_deposit(
        self,
        amount,
        source="usage",
        pos_order=False,
        pos_payment=False,
        reference=False,
    ):
        self.ensure_one()
        if amount < 0:
            raise ValidationError(_("Consumed deposit amount must be positive."))
        if not self.is_custom_member:
            raise UserError(_("Only custom members can use deposit payments."))
        self._lock_membership_row()
        available_balance = self._get_membership_deposit_totals().get(self.id, 0.0)
        if available_balance + 1e-6 < amount:
            raise UserError(
                _(
                    "Member %s does not have enough deposit balance. Available: %.2f, requested: %.2f."
                )
                % (self.display_name, available_balance, amount)
            )
        return self.env["membership.deposit.ledger"].create(
            {
                "partner_id": self.id,
                "company_id": self.company_id.id or self.env.company.id,
                "amount": amount,
                "direction": "out",
                "source": source,
                "pos_order_id": pos_order.id if pos_order else False,
                "pos_payment_id": pos_payment.id if pos_payment else False,
                "reference": reference or False,
                "state": "posted",
            }
        )

    def refund_membership_deposit(self, amount, reference=False, pos_order=False):
        return self.add_membership_deposit(
            amount,
            source="refund",
            pos_order=pos_order,
            reference=reference,
        )

    def add_membership_points(self, points, source="manual", pos_order=False, reference=False):
        self.ensure_one()
        if points < 0:
            raise ValidationError(_("Point amount must be positive."))
        if not self.is_custom_member:
            raise UserError(_("Only custom members can receive points."))
        return self.env["membership.point.ledger"].create(
            {
                "partner_id": self.id,
                "company_id": self.company_id.id or self.env.company.id,
                "points": points,
                "direction": "earned",
                "source": source,
                "pos_order_id": pos_order.id if pos_order else False,
                "reference": reference or False,
            }
        )

    def redeem_membership_points(self, points, source="reward", pos_order=False, reference=False):
        self.ensure_one()
        if points < 0:
            raise ValidationError(_("Redeemed point amount must be positive."))
        available_points = self._get_membership_point_totals().get(self.id, 0)
        if available_points < points:
            raise UserError(_("Member %s does not have enough points.") % self.display_name)
        return self.env["membership.point.ledger"].create(
            {
                "partner_id": self.id,
                "company_id": self.company_id.id or self.env.company.id,
                "points": points,
                "direction": "redeemed",
                "source": source,
                "pos_order_id": pos_order.id if pos_order else False,
                "reference": reference or False,
            }
        )

    def get_membership_snapshot(self):
        self.ensure_one()
        deposit_total = self._get_membership_deposit_totals().get(self.id, 0.0)
        point_total = self._get_membership_point_totals().get(self.id, 0)
        return {
            "id": self.id,
            "name": self.display_name,
            "custom_member_barcode": self.custom_member_barcode,
            "custom_member_type": self.custom_member_type,
            "is_custom_member": self.is_custom_member,
            "total_deposit_balance": deposit_total,
            "total_points": point_total,
            "membership_portal_enabled": self.membership_portal_enabled,
            "membership_last_checkin_date": self.membership_last_checkin_date,
        }

    def get_daily_reward_status(self, company=False):
        self.ensure_one()
        company = company or self.company_id or self.env.company
        today = fields.Date.context_today(self)
        reward_config_model = self.env["daily.free.product.config"].sudo()
        reward_config = reward_config_model.get_active_reward_for_day(company.id, today)
        reward_products = reward_config.get_reward_products() if reward_config else self.env["product.product"]
        claim_log = self.env["daily.claim.log"].sudo().search(
            [
                ("partner_id", "=", self.id),
                ("company_id", "=", company.id),
                ("date", "=", today),
            ],
            limit=1,
        )
        return {
            "date": today,
            "eligible": bool(self.is_custom_member and reward_config and reward_products and not claim_log),
            "already_claimed": bool(claim_log),
            "reward_product_id": reward_products[:1].id if reward_products else False,
            "reward_product_name": reward_products[:1].display_name if reward_products else False,
            "reward_product_ids": reward_products.ids,
            "reward_products": [
                {
                    "id": product.id,
                    "name": product.display_name,
                }
                for product in reward_products
            ],
        }

    def consume_daily_reward(self, product, pos_order=False):
        self.ensure_one()
        today = fields.Date.context_today(self)
        try:
            with self.env.cr.savepoint():
                log = self.env["daily.claim.log"].create(
                    {
                        "partner_id": self.id,
                        "company_id": self.company_id.id or self.env.company.id,
                        "date": today,
                        "product_id": product.id,
                        "pos_order_id": pos_order.id if pos_order else False,
                    }
                )
        except IntegrityError as err:
            raise UserError(_("Daily reward hanya dapat diklaim 1 kali per hari.")) from err
        self.membership_last_checkin_date = today
        return log

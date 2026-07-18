import random
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosSupervisorPin(models.Model):
    _name = "pos.supervisor.pin"
    _description = "POS Supervisor PIN"
    _order = "company_id, id desc"

    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    pin_code = fields.Char(
        string="PIN",
        required=True,
        copy=False,
        readonly=True,
    )
    last_generated_at = fields.Datetime(
        string="Last Generated At",
        readonly=True,
        copy=False,
    )
    last_used_at = fields.Datetime(
        string="Last Used At",
        readonly=True,
        copy=False,
    )
    last_used_by_id = fields.Many2one(
        "res.users",
        string="Last Used By",
        readonly=True,
        copy=False,
    )
    backend_revision_limit_mode = fields.Selection(
        [
            ("same_week", "Same Calendar Week"),
            ("rolling_days", "Rolling Days"),
        ],
        string="Backend Revision Window",
        required=True,
        default="same_week",
    )
    backend_revision_limit_days = fields.Integer(
        string="Rolling Days Limit",
        default=7,
    )
    allow_sunday_extension = fields.Boolean(
        string="Allow Sunday H+1",
        default=True,
        help="If enabled, Sunday transactions can still be revised on Monday.",
    )
    backend_revision_override_enabled = fields.Boolean(
        string="Emergency Override Enabled",
        default=False,
        copy=False,
    )
    backend_revision_override_until = fields.Datetime(
        string="Override Until",
        copy=False,
    )
    backend_revision_override_active = fields.Boolean(
        string="Override Active",
        compute="_compute_backend_revision_override_active",
    )

    _sql_constraints = [
        ("pos_supervisor_pin_company_unique", "unique(company_id)", "Only one supervisor PIN is allowed per company."),
    ]

    @api.depends("company_id")
    def _compute_name(self):
        for record in self:
            company_name = record.company_id.display_name or _("Company")
            record.name = _("Supervisor PIN - %s") % company_name

    @api.depends("backend_revision_override_enabled", "backend_revision_override_until")
    def _compute_backend_revision_override_active(self):
        now = fields.Datetime.now()
        for record in self:
            record.backend_revision_override_active = bool(
                record.backend_revision_override_enabled
                and (not record.backend_revision_override_until or record.backend_revision_override_until >= now)
            )

    @api.constrains("pin_code")
    def _check_pin_code(self):
        for record in self:
            if not record.pin_code or len(record.pin_code) != 5 or not record.pin_code.isdigit():
                raise ValidationError(_("Supervisor PIN must contain exactly 5 numeric digits."))

    @api.model_create_multi
    def create(self, vals_list):
        now = fields.Datetime.now()
        for vals in vals_list:
            vals.setdefault("company_id", self.env.company.id)
            vals["pin_code"] = vals.get("pin_code") or self._generate_pin_code()
            vals.setdefault("last_generated_at", now)
        return super().create(vals_list)

    def write(self, vals):
        if "pin_code" in vals and vals.get("pin_code"):
            vals.setdefault("last_generated_at", fields.Datetime.now())
        if vals.get("backend_revision_limit_mode") != "rolling_days" and "backend_revision_limit_mode" in vals:
            vals.setdefault("backend_revision_limit_days", 7)
        return super().write(vals)

    @api.constrains("backend_revision_limit_days")
    def _check_backend_revision_limit_days(self):
        for record in self:
            if record.backend_revision_limit_days < 1:
                raise ValidationError(_("Rolling days limit must be at least 1 day."))

    @api.model
    def _generate_pin_code(self):
        return "".join(random.SystemRandom().choices("0123456789", k=5))

    @api.model
    def get_company_pin(self, company):
        company = company or self.env.company
        pin = self.search([("company_id", "=", company.id)], limit=1)
        if not pin:
            pin = self.create({"company_id": company.id})
        return pin

    def get_masked_pin(self):
        self.ensure_one()
        return "***%s" % (self.pin_code[-2:] if self.pin_code else "")

    def verify_pin(self, input_pin):
        self.ensure_one()
        return (input_pin or "").strip() == (self.pin_code or "")

    def consume_pin(self, input_pin, used_by):
        self.ensure_one()
        if not self.verify_pin(input_pin):
            raise ValidationError(_("Invalid supervisor PIN."))

        masked_pin = self.get_masked_pin()
        now = fields.Datetime.now()
        self.write(
            {
                "last_used_at": now,
                "last_used_by_id": used_by.id if used_by else False,
                "pin_code": self._generate_pin_code(),
                "last_generated_at": now,
            }
        )
        return masked_pin

    def action_regenerate_pin(self):
        now = fields.Datetime.now()
        for record in self:
            record.write(
                {
                    "pin_code": self._generate_pin_code(),
                    "last_generated_at": now,
                }
            )
        return True

    def action_enable_backend_revision_override(self):
        now = fields.Datetime.now()
        for record in self:
            override_until = record.backend_revision_override_until
            if not override_until or override_until < now:
                override_until = now + timedelta(days=1)
            record.write(
                {
                    "backend_revision_override_enabled": True,
                    "backend_revision_override_until": override_until,
                }
            )
        return True

    def action_disable_backend_revision_override(self):
        self.write(
            {
                "backend_revision_override_enabled": False,
                "backend_revision_override_until": False,
            }
        )
        return True

    def _evaluate_backend_revision_window(self, order):
        self.ensure_one()
        order.ensure_one()
        now = fields.Datetime.now()
        order_datetime = fields.Datetime.to_datetime(order.date_order or now)
        order_date = order_datetime.date()
        today = now.date()

        if self.backend_revision_override_enabled:
            if not self.backend_revision_override_until or self.backend_revision_override_until >= now:
                override_note = (
                    _("Emergency override is active until %s.") % self.backend_revision_override_until
                    if self.backend_revision_override_until
                    else _("Emergency override is active without an end time.")
                )
                return {
                    "allowed": True,
                    "policy_status": "override",
                    "policy_note": override_note,
                }

        if self.backend_revision_limit_mode == "rolling_days":
            age_days = (today - order_date).days
            allowed = age_days <= self.backend_revision_limit_days
            note = _(
                "Rolling window policy: order age %(age)s day(s), limit %(limit)s day(s)."
            ) % {
                "age": age_days,
                "limit": self.backend_revision_limit_days,
            }
            return {
                "allowed": allowed,
                "policy_status": "within_window" if allowed else "blocked",
                "policy_note": note,
            }

        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        allowed = week_start <= order_date <= week_end
        note = _(
            "Same-week policy: order date %(order_date)s, allowed week %(week_start)s to %(week_end)s."
        ) % {
            "order_date": order_date,
            "week_start": week_start,
            "week_end": week_end,
        }
        if not allowed and self.allow_sunday_extension and order_date.weekday() == 6 and today == order_date + timedelta(days=1):
            allowed = True
            note = _(
                "Sunday extension policy: Sunday transaction dated %(order_date)s is allowed on Monday."
            ) % {
                "order_date": order_date,
            }
        return {
            "allowed": allowed,
            "policy_status": "within_window" if allowed else "blocked",
            "policy_note": note,
        }

    def check_backend_revision_window(self, order, action_name):
        self.ensure_one()
        result = self._evaluate_backend_revision_window(order)
        if result["allowed"]:
            return result
        raise UserError(
            _(
                "%(action)s is blocked by the backend revision security window. %(detail)s"
            )
            % {
                "action": action_name,
                "detail": result["policy_note"],
            }
        )

    @api.model
    def action_open_company_pin(self):
        pin = self.get_company_pin(self.env.company)
        return {
            "type": "ir.actions.act_window",
            "name": _("Supervisor PIN"),
            "res_model": "pos.supervisor.pin",
            "view_mode": "form",
            "res_id": pin.id,
            "target": "current",
        }

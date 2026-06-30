import io
import math
import random
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytz

from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import xlsxwriter


class PosSalesSimulation(models.Model):
    _name = "pos.sales.simulation"
    _description = "POS Sales Simulation"
    _order = "date_from desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done")],
        default="draft",
        required=True,
        copy=False,
    )
    pos_config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        default=lambda self: self._default_pos_config_id(),
        check_company=True,
    )
    pos_config_selector = fields.Selection(
        selection="_selection_available_pos_configs",
        string="Point of Sale",
        default=lambda self: self._default_pos_config_selector(),
        copy=False,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        store=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="pos_config_id.currency_id",
        store=True,
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
        required=True,
        check_company=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        required=True,
        default=lambda self: self.env.user,
    )
    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    opening_hour = fields.Float(
        string="Opening Hour",
        required=True,
        default=8.0,
    )
    closing_hour = fields.Float(
        string="Closing Hour",
        required=True,
        default=22.0,
    )
    peak_start_hour = fields.Float(
        string="Peak Start Hour",
        required=True,
        default=11.0,
    )
    peak_end_hour = fields.Float(
        string="Peak End Hour",
        required=True,
        default=14.0,
    )
    peak_ratio = fields.Float(
        string="Peak Ratio",
        required=True,
        default=0.6,
    )
    target_revenue = fields.Monetary(required=True, currency_field="currency_id")
    target_tolerance_pct = fields.Float(
        string="Target Tolerance (%)",
        default=5.0,
    )
    transaction_count = fields.Integer(required=True, default=10)
    transaction_count_guidance = fields.Char(
        compute="_compute_transaction_count_guidance",
        string="Transaction Count Guidance",
    )
    target_revenue_window = fields.Char(
        compute="_compute_transaction_count_guidance",
        string="Target Revenue Window",
    )
    min_transaction_amount = fields.Monetary(
        string="Minimum Ticket",
        required=True,
        currency_field="currency_id",
        default=50.0,
    )
    max_transaction_amount = fields.Monetary(
        string="Maximum Ticket",
        required=True,
        currency_field="currency_id",
        default=500.0,
    )
    min_lines_per_order = fields.Integer(
        string="Minimum Basket Lines",
        required=True,
        default=2,
    )
    max_lines_per_order = fields.Integer(
        string="Maximum Basket Lines",
        required=True,
        default=4,
    )
    pos_category_ids = fields.Many2many(
        "pos.category",
        "pos_sales_simulation_pos_category_rel",
        "simulation_id",
        "category_id",
        string="Product POS Categories",
        help="Optional POS category override used to resolve the product source.",
    )
    customer_ids = fields.Many2many(
        "res.partner",
        "pos_sales_simulation_partner_rel",
        "simulation_id",
        "partner_id",
        string="Customer Override",
        help="Optional customer override used when generating simulation transactions.",
    )
    product_ids = fields.Many2many(
        "product.product",
        "pos_sales_simulation_product_rel",
        "simulation_id",
        "product_id",
        string="Product Override",
        help="Optional product override used when generating simulation transactions.",
    )
    payment_method_ids = fields.Many2many(
        "pos.payment.method",
        "pos_sales_simulation_payment_method_rel",
        "simulation_id",
        "payment_method_id",
        string="Payment Method Override",
        help="Optional payment method override used when generating simulation transactions.",
    )
    available_payment_method_ids = fields.Many2many(
        "pos.payment.method",
        related="pos_config_id.payment_method_ids",
        string="Available Payment Methods",
        readonly=True,
    )
    generated_at = fields.Datetime(readonly=True, copy=False)
    transaction_ids = fields.One2many(
        "pos.sales.simulation.transaction",
        "batch_id",
        string="Transactions",
    )
    transaction_count_generated = fields.Integer(
        compute="_compute_summary_fields",
        string="Generated Transactions",
    )
    total_revenue_actual = fields.Monetary(
        compute="_compute_summary_fields",
        currency_field="currency_id",
        string="Actual Revenue",
    )
    revenue_gap = fields.Monetary(
        compute="_compute_summary_fields",
        currency_field="currency_id",
        string="Revenue Gap",
    )
    resolved_customer_count = fields.Integer(
        compute="_compute_resolved_source_fields",
        string="Resolved Customer Count",
    )
    resolved_product_count = fields.Integer(
        compute="_compute_resolved_source_fields",
        string="Resolved Product Count",
    )
    resolved_payment_count = fields.Integer(
        compute="_compute_resolved_source_fields",
        string="Resolved Payment Method Count",
    )
    resolved_pos_category_names = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Resolved POS Categories",
    )
    resolved_customer_source = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Customer Source",
    )
    resolved_product_source = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Product Source",
    )
    resolved_payment_source = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Payment Source",
    )
    selected_payment_method_names = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Selected Payment Methods",
    )
    basket_profile_summary = fields.Char(
        compute="_compute_resolved_source_fields",
        string="Basket Profile",
    )

    @api.depends("target_revenue", "transaction_ids.amount_total")
    def _compute_summary_fields(self):
        for simulation in self:
            simulation.transaction_count_generated = len(simulation.transaction_ids)
            simulation.total_revenue_actual = sum(simulation.transaction_ids.mapped("amount_total"))
            simulation.revenue_gap = simulation.target_revenue - simulation.total_revenue_actual

    @api.depends(
        "target_revenue",
        "target_tolerance_pct",
        "min_transaction_amount",
        "max_transaction_amount",
        "currency_id",
    )
    def _compute_transaction_count_guidance(self):
        for simulation in self:
            bounds = simulation._get_transaction_count_bounds_for_target()
            amount_window = simulation._get_target_amount_window()
            simulation.target_revenue_window = (
                _(
                    "%(minimum)s - %(maximum)s",
                    minimum=simulation._format_currency_amount(amount_window[0]),
                    maximum=simulation._format_currency_amount(amount_window[1]),
                )
                if amount_window
                else False
            )
            if not bounds:
                simulation.transaction_count_guidance = False
                continue
            minimum_count, maximum_count = bounds
            if minimum_count > maximum_count:
                simulation.transaction_count_guidance = _(
                    "Target revenue is outside the current ticket range."
                )
                continue
            simulation.transaction_count_guidance = _(
                "Recommended transaction count: %(minimum)s-%(maximum)s",
                minimum=minimum_count,
                maximum=maximum_count,
            )

    @api.depends(
        "customer_ids",
        "product_ids",
        "payment_method_ids",
        "pos_category_ids",
        "pos_config_id",
        "pos_config_id.simulation_pos_category_ids",
        "pos_config_id.simulation_product_rule_ids.active",
        "pos_config_id.simulation_product_rule_ids.product_id",
        "pos_config_id.simulation_payment_rule_ids.active",
        "pos_config_id.simulation_payment_rule_ids.payment_method_id",
        "pos_config_id.payment_method_ids",
        "min_lines_per_order",
        "max_lines_per_order",
        "peak_start_hour",
        "peak_end_hour",
        "peak_ratio",
    )
    def _compute_resolved_source_fields(self):
        for simulation in self:
            customer_pool = simulation._get_customer_pool(raise_if_empty=False)
            product_candidates = simulation._get_product_candidates(raise_if_empty=False)
            payment_candidates = simulation._get_payment_candidates(raise_if_empty=False)
            category_pool = simulation._get_product_category_pool()
            simulation.resolved_customer_count = len(customer_pool)
            simulation.resolved_product_count = len({candidate["product"].id for candidate in product_candidates})
            simulation.resolved_payment_count = len(
                {candidate["payment_method"].id for candidate in payment_candidates}
            )
            simulation.resolved_pos_category_names = ", ".join(category_pool.mapped("display_name")) or _("All POS Categories")
            simulation.resolved_customer_source = simulation._describe_customer_source()
            simulation.resolved_product_source = simulation._describe_product_source()
            simulation.resolved_payment_source = simulation._describe_payment_source()
            simulation.selected_payment_method_names = ", ".join(simulation.payment_method_ids.mapped("name"))
            simulation.basket_profile_summary = _(
                "%(min)s-%(max)s lines | Peak %(ratio)s%% (%(start)s-%(end)s)",
                min=simulation.min_lines_per_order,
                max=simulation.max_lines_per_order,
                ratio=int(round((simulation.peak_ratio or 0.0) * 100)),
                start=simulation._format_hour(simulation.peak_start_hour),
                end=simulation._format_hour(simulation.peak_end_hour),
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("pos_config_selector") and not vals.get("pos_config_id"):
                vals["pos_config_id"] = int(vals["pos_config_selector"])
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("pos.sales.simulation") or _("New")
            if vals.get("pos_config_id"):
                config = self.env["pos.config"].browse(vals["pos_config_id"])
                self._apply_pos_config_defaults_to_vals(vals, config)
            self._normalize_target_tolerance_vals(vals)
        return super().create(vals_list)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        config = False
        if vals.get("pos_config_id"):
            config = self.env["pos.config"].browse(vals["pos_config_id"])
        else:
            config = self._get_default_pos_config()
            if config:
                vals["pos_config_id"] = config.id
        if not config:
            return vals
        if not vals.get("pos_config_selector"):
            vals["pos_config_selector"] = str(config.id)
        if "payment_method_ids" not in vals or not vals.get("payment_method_ids"):
            self._apply_pos_config_defaults_to_vals(vals, config)
        elif not vals.get("pricelist_id"):
            self._apply_pos_config_defaults_to_vals(vals, config)
        return vals

    def write(self, vals):
        if vals.get("pos_config_selector") and not vals.get("pos_config_id"):
            vals["pos_config_id"] = int(vals["pos_config_selector"])
        if "pos_config_id" in vals and vals.get("pos_config_id"):
            vals["pos_config_selector"] = str(vals["pos_config_id"])
            if vals.get("target_tolerance_pct") is None or vals.get("target_tolerance_pct") is False:
                vals["target_tolerance_pct"] = self.env["pos.config"].browse(vals["pos_config_id"]).simulation_target_tolerance_pct
        self._normalize_target_tolerance_vals(vals)
        if any(
            key in vals
            for key in (
                "target_revenue",
                "target_tolerance_pct",
                "transaction_count",
                "min_transaction_amount",
                "max_transaction_amount",
            )
        ):
            for simulation in self:
                merged_vals = {
                    "company_id": vals.get("company_id", simulation.company_id.id),
                    "pos_config_id": vals.get("pos_config_id", simulation.pos_config_id.id),
                    "target_revenue": vals.get("target_revenue", simulation.target_revenue),
                    "target_tolerance_pct": vals.get("target_tolerance_pct", simulation.target_tolerance_pct),
                    "transaction_count": vals.get("transaction_count", simulation.transaction_count),
                    "min_transaction_amount": vals.get(
                        "min_transaction_amount",
                        simulation.min_transaction_amount,
                    ),
                    "max_transaction_amount": vals.get(
                        "max_transaction_amount",
                        simulation.max_transaction_amount,
                    ),
                }
                self._autoadjust_transaction_count_vals(merged_vals)
                if "transaction_count" in merged_vals:
                    vals["transaction_count"] = merged_vals["transaction_count"]
        return super().write(vals)

    @api.onchange("pos_config_id")
    def _onchange_pos_config_id(self):
        if not self.pos_config_id:
            return
        self._apply_pos_config_defaults_to_record(self.pos_config_id)
        self._autoadjust_transaction_count()

    @api.onchange("pos_config_selector")
    def _onchange_pos_config_selector(self):
        if not self.pos_config_selector:
            self.pos_config_id = False
            return
        self.pos_config_id = self.env["pos.config"].browse(int(self.pos_config_selector))
        self._apply_pos_config_defaults_to_record(self.pos_config_id)
        self._autoadjust_transaction_count()

    @api.onchange("target_revenue", "target_tolerance_pct", "min_transaction_amount", "max_transaction_amount")
    def _onchange_transaction_count_inputs(self):
        self._autoadjust_transaction_count()

    @api.constrains(
        "date_from",
        "date_to",
        "opening_hour",
        "closing_hour",
        "peak_start_hour",
        "peak_end_hour",
        "peak_ratio",
        "transaction_count",
        "target_revenue",
        "target_tolerance_pct",
        "min_transaction_amount",
        "max_transaction_amount",
        "min_lines_per_order",
        "max_lines_per_order",
    )
    def _check_simulation_constraints(self):
        for simulation in self:
            simulation._validate_generation_inputs()

    def _apply_pos_config_defaults_to_vals(self, vals, config):
        vals["company_id"] = config.company_id.id
        vals["pos_config_selector"] = str(config.id)
        vals.setdefault("opening_hour", config.simulation_opening_hour)
        vals.setdefault("closing_hour", config.simulation_closing_hour)
        vals.setdefault("peak_start_hour", config.simulation_peak_start_hour)
        vals.setdefault("peak_end_hour", config.simulation_peak_end_hour)
        vals.setdefault("peak_ratio", config.simulation_peak_ratio)
        vals.setdefault("min_transaction_amount", config.simulation_min_transaction_amount)
        vals.setdefault("max_transaction_amount", config.simulation_max_transaction_amount)
        if vals.get("target_tolerance_pct") is None or vals.get("target_tolerance_pct") is False:
            vals["target_tolerance_pct"] = config.simulation_target_tolerance_pct
        vals.setdefault("min_lines_per_order", config.simulation_min_lines_per_order)
        vals.setdefault("max_lines_per_order", config.simulation_max_lines_per_order)
        default_pricelist = self._get_default_pricelist(config)
        if default_pricelist:
            vals.setdefault("pricelist_id", default_pricelist.id)
        if "pos_category_ids" not in vals:
            vals["pos_category_ids"] = [Command.set(config.simulation_pos_category_ids.ids)]
        if "payment_method_ids" not in vals:
            payment_method_ids = config.simulation_payment_rule_ids.filtered("active").mapped("payment_method_id").ids
            vals["payment_method_ids"] = [Command.set(payment_method_ids or config.payment_method_ids.ids)]
        self._autoadjust_transaction_count_vals(vals)

    def _apply_pos_config_defaults_to_record(self, config):
        self.pos_config_selector = str(config.id)
        self.company_id = config.company_id
        self.opening_hour = config.simulation_opening_hour
        self.closing_hour = config.simulation_closing_hour
        self.peak_start_hour = config.simulation_peak_start_hour
        self.peak_end_hour = config.simulation_peak_end_hour
        self.peak_ratio = config.simulation_peak_ratio
        self.min_transaction_amount = config.simulation_min_transaction_amount
        self.max_transaction_amount = config.simulation_max_transaction_amount
        self.target_tolerance_pct = config.simulation_target_tolerance_pct
        self.min_lines_per_order = config.simulation_min_lines_per_order
        self.max_lines_per_order = config.simulation_max_lines_per_order
        self.pos_category_ids = config.simulation_pos_category_ids
        default_pricelist = self._get_default_pricelist(config)
        if default_pricelist:
            self.pricelist_id = default_pricelist
        self.payment_method_ids = (
            config.simulation_payment_rule_ids.filtered("active").mapped("payment_method_id")
            or config.payment_method_ids
        )

    @api.model
    def _normalize_target_tolerance_vals(self, vals):
        if "target_tolerance_pct" in vals and vals.get("target_tolerance_pct") not in (None, False):
            return vals
        vals["target_tolerance_pct"] = 5.0
        return vals

    def _validate_generation_inputs(self):
        for simulation in self:
            if not simulation.company_id:
                raise ValidationError(_("Company is required."))
            if not simulation.date_from or not simulation.date_to:
                raise ValidationError(_("Simulation period is required."))
            if simulation.date_from > simulation.date_to:
                raise ValidationError(_("Start date must be earlier than or equal to the end date."))
            if not 0.0 <= simulation.opening_hour < 24.0:
                raise ValidationError(_("Opening hour must be between 00:00 and 24:00."))
            if not 0.0 < simulation.closing_hour <= 24.0:
                raise ValidationError(_("Closing hour must be between 00:00 and 24:00."))
            if simulation.opening_hour >= simulation.closing_hour:
                raise ValidationError(_("Opening hour must be earlier than the closing hour."))
            if not 0.0 <= simulation.peak_start_hour < 24.0:
                raise ValidationError(_("Peak start hour must be between 00:00 and 24:00."))
            if not 0.0 < simulation.peak_end_hour <= 24.0:
                raise ValidationError(_("Peak end hour must be between 00:00 and 24:00."))
            if simulation.peak_start_hour >= simulation.peak_end_hour:
                raise ValidationError(_("Peak start hour must be earlier than the peak end hour."))
            if not 0.0 <= simulation.peak_ratio <= 1.0:
                raise ValidationError(_("Peak ratio must be between 0 and 1."))
            if simulation.transaction_count <= 0:
                raise ValidationError(_("Transaction count must be greater than zero."))
            if simulation.target_revenue <= 0:
                raise ValidationError(_("Target revenue must be greater than zero."))
            if simulation.target_tolerance_pct < 0 or simulation.target_tolerance_pct > 100:
                raise ValidationError(_("Target tolerance must be between 0 and 100 percent."))
            if simulation.min_transaction_amount <= 0 or simulation.max_transaction_amount <= 0:
                raise ValidationError(_("Minimum and maximum ticket amounts must be greater than zero."))
            if simulation.min_transaction_amount > simulation.max_transaction_amount:
                raise ValidationError(_("Minimum ticket amount must not exceed the maximum ticket amount."))
            if simulation.min_lines_per_order <= 0 or simulation.max_lines_per_order <= 0:
                raise ValidationError(_("Basket line counts must be greater than zero."))
            if simulation.min_lines_per_order > simulation.max_lines_per_order:
                raise ValidationError(_("Minimum basket lines must not exceed the maximum basket lines."))

            feasible_window = simulation._get_feasible_total_amount_window()
            if not feasible_window:
                count_bounds = simulation._get_transaction_count_bounds_for_target()
                raise ValidationError(
                    _(
                        "Target revenue must fit the ticket range for the requested transaction count, "
                        "including the allowed tolerance.\n"
                        "Recommended transaction count: %(minimum)s to %(maximum)s.",
                        minimum=count_bounds[0] if count_bounds else 0,
                        maximum=count_bounds[1] if count_bounds else 0,
                    )
                )

    def _get_default_pricelist(self, config):
        pricelist = config.pricelist_id or config.available_pricelist_ids[:1]
        if pricelist:
            return pricelist
        return self.env["product.pricelist"].search(
            [("company_id", "in", [False, config.company_id.id])],
            limit=1,
        )

    def _amount_to_units(self, amount):
        self.ensure_one()
        unit_value = Decimal(str(self.currency_id.rounding or 0.01))
        return int(
            (Decimal(str(amount)) / unit_value).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )

    def _units_to_amount(self, amount_units):
        self.ensure_one()
        unit_value = Decimal(str(self.currency_id.rounding or 0.01))
        return float(Decimal(amount_units) * unit_value)

    def _format_currency_amount(self, amount):
        self.ensure_one()
        symbol = self.currency_id.symbol or ""
        return f"{symbol}{amount:,.2f}".strip()

    def _format_hour(self, hour_value):
        self.ensure_one()
        hours = int(hour_value or 0.0)
        minutes = int(round(((hour_value or 0.0) - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        return f"{hours:02d}:{minutes:02d}"

    def _get_target_amount_window(self):
        self.ensure_one()
        if not self.target_revenue or self.target_revenue <= 0:
            return False
        tolerance_ratio = max(self.target_tolerance_pct or 0.0, 0.0) / 100.0
        minimum_amount = self.currency_id.round(self.target_revenue * (1 - tolerance_ratio))
        maximum_amount = self.currency_id.round(self.target_revenue * (1 + tolerance_ratio))
        return minimum_amount, maximum_amount

    def _get_target_total_unit_window(self):
        self.ensure_one()
        amount_window = self._get_target_amount_window()
        if not amount_window:
            return False
        return tuple(self._amount_to_units(amount) for amount in amount_window)

    def _get_feasible_total_unit_window(self):
        self.ensure_one()
        target_window = self._get_target_total_unit_window()
        if not target_window or self.transaction_count <= 0:
            return False
        min_units = self._amount_to_units(self.min_transaction_amount)
        max_units = self._amount_to_units(self.max_transaction_amount)
        minimum_total = max(target_window[0], min_units * self.transaction_count)
        maximum_total = min(target_window[1], max_units * self.transaction_count)
        if minimum_total > maximum_total:
            return False
        nominal_total = self._amount_to_units(self.target_revenue)
        mode_total = min(max(nominal_total, minimum_total), maximum_total)
        return minimum_total, maximum_total, mode_total

    def _get_feasible_total_amount_window(self):
        self.ensure_one()
        unit_window = self._get_feasible_total_unit_window()
        if not unit_window:
            return False
        return tuple(self._units_to_amount(value) for value in unit_window[:2])

    def _get_transaction_count_bounds_for_target(self):
        self.ensure_one()
        if (
            not self.currency_id
            or self.target_revenue <= 0
            or self.min_transaction_amount <= 0
            or self.max_transaction_amount <= 0
        ):
            return False
        min_ticket_units = self._amount_to_units(self.min_transaction_amount)
        max_ticket_units = self._amount_to_units(self.max_transaction_amount)
        target_window = self._get_target_total_unit_window()
        if min_ticket_units <= 0 or max_ticket_units <= 0 or not target_window:
            return False
        minimum_count = math.ceil(target_window[0] / max_ticket_units)
        maximum_count = target_window[1] // min_ticket_units
        return minimum_count, maximum_count

    def _get_preferred_transaction_count(self):
        self.ensure_one()
        bounds = self._get_transaction_count_bounds_for_target()
        if not bounds:
            return False
        minimum_count, maximum_count = bounds
        if minimum_count > maximum_count:
            return False
        average_ticket = (self.min_transaction_amount + self.max_transaction_amount) / 2.0
        preferred_count = round(self.target_revenue / average_ticket) if average_ticket > 0 else minimum_count
        return min(max(preferred_count, minimum_count), maximum_count)

    def _autoadjust_transaction_count(self):
        for simulation in self:
            bounds = simulation._get_transaction_count_bounds_for_target()
            if not bounds:
                continue
            minimum_count, maximum_count = bounds
            if minimum_count > maximum_count:
                continue
            preferred_count = simulation._get_preferred_transaction_count() or minimum_count
            current_count = simulation.transaction_count or 0
            if current_count <= 0:
                simulation.transaction_count = preferred_count
            elif current_count < minimum_count:
                simulation.transaction_count = preferred_count
            elif current_count > maximum_count:
                simulation.transaction_count = preferred_count

    @api.model
    def _autoadjust_transaction_count_vals(self, vals):
        target_revenue = vals.get("target_revenue")
        target_tolerance_pct = vals.get("target_tolerance_pct", 5.0)
        min_amount = vals.get("min_transaction_amount")
        max_amount = vals.get("max_transaction_amount")
        if target_revenue in (None, False) or min_amount in (None, False) or max_amount in (None, False):
            return vals

        currency = False
        pos_config_id = vals.get("pos_config_id")
        if pos_config_id:
            currency = self.env["pos.config"].browse(pos_config_id).currency_id
        if not currency:
            company_id = vals.get("company_id") or self.env.company.id
            currency = self.env["res.company"].browse(company_id).currency_id
        if not currency:
            return vals

        rounding = Decimal(str(currency.rounding or 0.01))
        total_units = int((Decimal(str(target_revenue)) / rounding).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        min_units = int((Decimal(str(min_amount)) / rounding).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        max_units = int((Decimal(str(max_amount)) / rounding).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        if total_units <= 0 or min_units <= 0 or max_units <= 0:
            return vals

        tolerance_ratio = max(float(target_tolerance_pct or 0.0), 0.0) / 100.0
        minimum_target_units = int(
            (Decimal(str(target_revenue * (1 - tolerance_ratio))) / rounding).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        maximum_target_units = int(
            (Decimal(str(target_revenue * (1 + tolerance_ratio))) / rounding).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )
        minimum_count = math.ceil(minimum_target_units / max_units)
        maximum_count = maximum_target_units // min_units
        if minimum_count > maximum_count:
            return vals

        average_ticket = (float(min_amount) + float(max_amount)) / 2.0
        preferred_count = round(float(target_revenue) / average_ticket) if average_ticket > 0 else minimum_count
        preferred_count = min(max(preferred_count, minimum_count), maximum_count)
        current_count = vals.get("transaction_count") or 0
        if current_count <= 0:
            vals["transaction_count"] = preferred_count
        elif current_count < minimum_count:
            vals["transaction_count"] = preferred_count
        elif current_count > maximum_count:
            vals["transaction_count"] = preferred_count
        return vals

    @api.model
    def _selection_available_pos_configs(self):
        company_ids = self.env.companies.ids or [self.env.company.id]
        configs = self.env["pos.config"].search([("company_id", "in", company_ids)], order="name")
        return [(str(config.id), config.display_name) for config in configs]

    @api.model
    def _get_default_pos_config(self):
        company_ids = self.env.companies.ids or [self.env.company.id]
        return self.env["pos.config"].search([("company_id", "in", company_ids)], order="name", limit=1)

    @api.model
    def _default_pos_config_id(self):
        config = self._get_default_pos_config()
        return config.id if config else False

    @api.model
    def _default_pos_config_selector(self):
        config = self._get_default_pos_config()
        return str(config.id) if config else False

    def _describe_customer_source(self):
        self.ensure_one()
        if self.customer_ids:
            return _("Manual customer override")
        return _("Auto active contacts")

    def _describe_product_source(self):
        self.ensure_one()
        if self.product_ids:
            return _("Manual product override")
        if self.pos_config_id.simulation_product_rule_ids.filtered("active"):
            return _("Weighted product rules")
        if self._get_product_category_pool():
            return _("POS categories")
        return _("All POS products")

    def _describe_payment_source(self):
        self.ensure_one()
        if self.payment_method_ids:
            payment_names = ", ".join(self.payment_method_ids.mapped("name"))
            if payment_names:
                return _("Manual payment override: %(methods)s", methods=payment_names)
            return _("Manual payment override")
        if self.pos_config_id.simulation_payment_rule_ids.filtered("active"):
            return _("Weighted payment rules")
        return _("POS payment methods")

    def _get_internal_partner_ids(self):
        return self.env["res.users"].search([("share", "=", False)]).mapped("partner_id").ids

    def _get_customer_pool(self, raise_if_empty=True):
        self.ensure_one()
        partners = self.customer_ids.filtered(lambda partner: partner.active)
        if not partners:
            excluded_partner_ids = self._get_internal_partner_ids()
            partners = self.env["res.partner"].search(
                [
                    ("active", "=", True),
                    ("type", "=", "contact"),
                    ("is_company", "=", False),
                    ("id", "not in", excluded_partner_ids),
                ]
            )
        if raise_if_empty and not partners:
            raise UserError(_("No eligible contact customer is available for the simulation."))
        return partners

    def _get_product_category_pool(self):
        self.ensure_one()
        return self.pos_category_ids or self.pos_config_id.simulation_pos_category_ids

    def _get_product_rule_candidates(self):
        self.ensure_one()
        categories = self._get_product_category_pool()
        rules = self.pos_config_id.simulation_product_rule_ids.filtered("active")
        if categories:
            rules = rules.filtered(lambda rule: rule.pos_category_id in categories)
        return rules.filtered(
            lambda rule: rule.product_id.active
            and rule.product_id.sale_ok
            and rule.product_id.product_tmpl_id.available_in_pos
        )

    def _get_product_candidates(self, raise_if_empty=True):
        self.ensure_one()
        candidates = []
        seen_product_ids = set()
        if self.product_ids:
            for product in self.product_ids.filtered(lambda product: product.active and product.sale_ok):
                candidates.append(
                    {
                        "product": product,
                        "weight": 1.0,
                        "min_qty": 1,
                        "max_qty": 3,
                    }
                )
                seen_product_ids.add(product.id)
        else:
            rules = self._get_product_rule_candidates()
            for rule in rules:
                if rule.product_id.id in seen_product_ids:
                    continue
                candidates.append(
                    {
                        "product": rule.product_id,
                        "weight": rule.weight,
                        "min_qty": rule.min_qty,
                        "max_qty": rule.max_qty,
                    }
                )
                seen_product_ids.add(rule.product_id.id)

            if not candidates:
                domain = [
                    ("active", "=", True),
                    ("sale_ok", "=", True),
                    ("product_tmpl_id.available_in_pos", "=", True),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.company_id.id),
                ]
                categories = self._get_product_category_pool()
                if categories:
                    domain.append(("product_tmpl_id.pos_categ_ids", "in", categories.ids))
                products = self.env["product.product"].search(domain)
                for product in products:
                    if product.id in seen_product_ids:
                        continue
                    candidates.append(
                        {
                            "product": product,
                            "weight": 1.0,
                            "min_qty": 1,
                            "max_qty": 3,
                        }
                    )
                    seen_product_ids.add(product.id)

        if raise_if_empty and not candidates:
            raise UserError(_("No POS product is available for the simulation."))
        return candidates

    def _get_payment_candidates(self, raise_if_empty=True):
        self.ensure_one()
        candidates = []
        seen_payment_method_ids = set()
        if self.payment_method_ids:
            for payment_method in self.payment_method_ids:
                candidates.append({"payment_method": payment_method, "weight": 1.0})
                seen_payment_method_ids.add(payment_method.id)
        else:
            rules = self.pos_config_id.simulation_payment_rule_ids.filtered("active")
            for rule in rules:
                if rule.payment_method_id.id in seen_payment_method_ids:
                    continue
                candidates.append({"payment_method": rule.payment_method_id, "weight": rule.weight})
                seen_payment_method_ids.add(rule.payment_method_id.id)

            if not candidates:
                payment_methods = self.pos_config_id.payment_method_ids
                for payment_method in payment_methods:
                    candidates.append({"payment_method": payment_method, "weight": 1.0})
                    seen_payment_method_ids.add(payment_method.id)

        if raise_if_empty and not candidates:
            raise UserError(_("No payment method is configured for this point of sale."))
        return candidates

    def _get_local_timezone(self):
        tz_name = self.env.user.tz or self.env.context.get("tz") or "UTC"
        return pytz.timezone(tz_name)

    def _clip_interval(self, start_hour, end_hour):
        start_second = int(max(start_hour, self.opening_hour) * 3600)
        end_second = min(int(min(end_hour, self.closing_hour) * 3600) - 1, 86399)
        if end_second < start_second:
            return None
        return start_second, end_second

    def _pick_second_from_intervals(self, intervals):
        valid_intervals = [interval for interval in intervals if interval]
        if not valid_intervals:
            return None
        interval = random.choice(valid_intervals)
        return random.randint(interval[0], interval[1])

    def _generate_timestamps(self):
        self.ensure_one()
        tz = self._get_local_timezone()
        start_date = fields.Date.to_date(self.date_from)
        end_date = fields.Date.to_date(self.date_to)
        day_count = (end_date - start_date).days + 1
        full_interval = self._clip_interval(self.opening_hour, self.closing_hour)
        peak_interval = self._clip_interval(self.peak_start_hour, self.peak_end_hour)
        non_peak_intervals = [
            self._clip_interval(self.opening_hour, self.peak_start_hour),
            self._clip_interval(self.peak_end_hour, self.closing_hour),
        ]

        datetimes = []
        for _index in range(self.transaction_count):
            selected_date = start_date + timedelta(days=random.randint(0, day_count - 1))
            use_peak = peak_interval and random.random() < (self.peak_ratio or 0.0)
            selected_second = None
            if use_peak:
                selected_second = self._pick_second_from_intervals([peak_interval])
            else:
                selected_second = self._pick_second_from_intervals(non_peak_intervals)
            if selected_second is None:
                selected_second = self._pick_second_from_intervals([peak_interval, full_interval])
            hours, remaining = divmod(selected_second, 3600)
            minutes, seconds = divmod(remaining, 60)
            local_dt = datetime.combine(
                selected_date,
                time(hour=hours, minute=minutes, second=seconds),
            )
            utc_dt = tz.localize(local_dt).astimezone(pytz.UTC).replace(tzinfo=None)
            datetimes.append(utc_dt)
        datetimes.sort()
        return datetimes

    def _distribute_amounts(self):
        self.ensure_one()
        feasible_window = self._get_feasible_total_unit_window()
        if not feasible_window:
            raise ValidationError(_("Unable to derive a feasible revenue total for the current target settings."))
        minimum_total_units, maximum_total_units, mode_total_units = feasible_window
        if minimum_total_units == maximum_total_units:
            total_units = minimum_total_units
        else:
            total_units = int(
                round(
                    random.triangular(
                        minimum_total_units,
                        maximum_total_units,
                        mode_total_units,
                    )
                )
            )
            total_units = min(max(total_units, minimum_total_units), maximum_total_units)
        min_units = self._amount_to_units(self.min_transaction_amount)
        max_units = self._amount_to_units(self.max_transaction_amount)
        amounts = [min_units] * self.transaction_count
        remaining = total_units - (min_units * self.transaction_count)
        capacity = max_units - min_units

        for index in range(self.transaction_count):
            remaining_slots = self.transaction_count - index - 1
            max_extra = min(capacity, remaining)
            min_extra = max(0, remaining - (remaining_slots * capacity))
            extra = random.randint(min_extra, max_extra) if max_extra > min_extra else min_extra
            amounts[index] += extra
            remaining -= extra

        random.shuffle(amounts)
        return [self._units_to_amount(amount_units) for amount_units in amounts]

    def _get_company_taxes(self, product):
        self.ensure_one()
        return product.taxes_id.filtered_domain(
            self.env["account.tax"]._check_company_domain(self.company_id)
        )

    def _get_fiscal_position(self, partner):
        self.ensure_one()
        return partner.property_account_position_id or self.pos_config_id.default_fiscal_position_id

    def _compute_target_amounts(self, taxes, partner, product, quantity, discounted_price):
        self.ensure_one()
        if not taxes:
            untaxed = discounted_price * quantity
            total = self.currency_id.round(untaxed)
            return {
                "price_subtotal": total,
                "price_subtotal_incl": total,
            }
        tax_result = taxes.compute_all(
            discounted_price,
            self.currency_id,
            quantity,
            product=product,
            partner=partner,
        )
        return {
            "price_subtotal": tax_result["total_excluded"],
            "price_subtotal_incl": tax_result["total_included"],
        }

    def _find_discounted_unit_price(self, taxes, partner, product, quantity, target_total):
        self.ensure_one()

        def _compute_total_included(discounted_price):
            totals = self._compute_target_amounts(
                taxes,
                partner,
                product,
                quantity,
                discounted_price,
            )
            return self.currency_id.round(totals["price_subtotal_incl"])

        low = 0.0
        high = max(target_total, 1.0)
        while float_compare(
            _compute_total_included(high),
            target_total,
            precision_rounding=self.currency_id.rounding,
        ) < 0:
            high *= 2
            if high > (target_total * 1000) + 1:
                break

        best = high
        for _attempt in range(80):
            current = (low + high) / 2
            current_total = _compute_total_included(current)
            if float_compare(
                current_total,
                target_total,
                precision_rounding=self.currency_id.rounding,
            ) >= 0:
                best = current
                high = current
            else:
                low = current

        step = max(self.currency_id.rounding / max(quantity, 1), 0.0001)
        for offset in range(-500, 501):
            candidate = max(best + ((step / 10.0) * offset), 0.0)
            candidate_total = _compute_total_included(candidate)
            if float_compare(
                candidate_total,
                target_total,
                precision_rounding=self.currency_id.rounding,
            ) == 0:
                return candidate

        raise ValidationError(
            _(
                "Could not match the requested ticket amount %(amount)s with the available tax setup.",
                amount=target_total,
            )
        )

    def _weighted_choice(self, candidates):
        self.ensure_one()
        if not candidates:
            return None
        total_weight = sum(max(candidate.get("weight", 0.0), 0.0) for candidate in candidates)
        if total_weight <= 0:
            return random.choice(candidates)
        threshold = random.uniform(0, total_weight)
        running = 0.0
        for candidate in candidates:
            running += max(candidate.get("weight", 0.0), 0.0)
            if threshold <= running:
                return candidate
        return candidates[-1]

    def _pick_customer(self, customers, previous_partner_id=False):
        self.ensure_one()
        customer_list = list(customers)
        if not customer_list:
            raise UserError(_("No eligible contact customer is available for the simulation."))
        if previous_partner_id and len(customer_list) > 1:
            filtered_customers = [partner for partner in customer_list if partner.id != previous_partner_id]
            if filtered_customers:
                customer_list = filtered_customers
        return random.choice(customer_list)

    def _select_product_candidates(self, candidates, line_count):
        self.ensure_one()
        remaining_candidates = list(candidates)
        selected_candidates = []
        used_product_ids = set()
        for _index in range(line_count):
            selectable_candidates = [
                candidate for candidate in remaining_candidates if candidate["product"].id not in used_product_ids
            ]
            if not selectable_candidates:
                selectable_candidates = list(candidates)
            chosen_candidate = self._weighted_choice(selectable_candidates)
            selected_candidates.append(chosen_candidate)
            used_product_ids.add(chosen_candidate["product"].id)
            remaining_candidates = [
                candidate for candidate in remaining_candidates if candidate["product"].id != chosen_candidate["product"].id
            ]
        return selected_candidates

    def _split_units_by_weights(self, total_units, weights, min_units=1):
        self.ensure_one()
        if not weights:
            return []
        units = [min_units] * len(weights)
        remaining_units = total_units - (len(weights) * min_units)
        if remaining_units < 0:
            raise ValidationError(_("Unable to split the ticket amount across the requested basket lines."))
        total_weight = sum(weights) or len(weights)
        raw_allocations = [remaining_units * weight / total_weight for weight in weights]
        integer_allocations = [int(math.floor(allocation)) for allocation in raw_allocations]
        fractions = [allocation - integer for allocation, integer in zip(raw_allocations, integer_allocations)]
        distributed_units = sum(integer_allocations)
        for index, extra_units in enumerate(integer_allocations):
            units[index] += extra_units
        leftover = remaining_units - distributed_units
        for index in sorted(range(len(fractions)), key=lambda idx: fractions[idx], reverse=True)[:leftover]:
            units[index] += 1
        return units

    def _build_line_vals_for_product(self, target_total, partner, product, fiscal_position, quantity):
        self.ensure_one()
        taxes = self._get_company_taxes(product)
        mapped_taxes = fiscal_position.map_tax(taxes) if fiscal_position else taxes
        discount_choices = [0.0, 0.0, 5.0, 10.0]
        random.shuffle(discount_choices)
        for discount in discount_choices:
            discount_factor = 1 - (discount / 100.0)
            if discount_factor <= 0:
                continue
            try:
                discounted_price = self._find_discounted_unit_price(
                    mapped_taxes,
                    partner,
                    product,
                    quantity,
                    target_total,
                )
            except ValidationError:
                continue

            price_unit = discounted_price / discount_factor
            totals = self._compute_target_amounts(
                mapped_taxes,
                partner,
                product,
                quantity,
                discounted_price,
            )
            actual_total = self.currency_id.round(totals["price_subtotal_incl"])
            if float_compare(
                actual_total,
                target_total,
                precision_rounding=self.currency_id.rounding,
            ) != 0:
                continue

            return {
                "product_id": product.id,
                "full_product_name": product.display_name,
                "qty": quantity,
                "discount": discount,
                "price_unit": price_unit,
                "tax_ids": [Command.set(taxes.ids)],
            }

        raise ValidationError(
            _(
                "Unable to match line total %(amount)s for product %(product)s.",
                amount=target_total,
                product=product.display_name,
            )
        )

    def _determine_line_count(self, product_candidates):
        self.ensure_one()
        unique_product_count = len({candidate["product"].id for candidate in product_candidates})
        if unique_product_count <= 1:
            return 1
        max_lines = min(self.max_lines_per_order, unique_product_count)
        min_lines = max(1, min(self.min_lines_per_order, max_lines))
        return random.randint(min_lines, max_lines)

    def _build_transaction_lines(self, amount_total, partner, product_candidates):
        self.ensure_one()
        fiscal_position = self._get_fiscal_position(partner)
        for _attempt in range(40):
            line_count = self._determine_line_count(product_candidates)
            selected_candidates = self._select_product_candidates(product_candidates, line_count)
            prepared_candidates = []
            for candidate in selected_candidates:
                prepared_candidates.append(
                    {
                        "product": candidate["product"],
                        "weight": candidate["weight"],
                        "qty": random.randint(candidate["min_qty"], candidate["max_qty"]),
                    }
                )

            amount_units = self._amount_to_units(amount_total)
            line_weights = [
                max(candidate["product"].product_tmpl_id.list_price * candidate["qty"], 1.0) * max(candidate["weight"], 0.1)
                for candidate in prepared_candidates
            ]
            line_amount_units = self._split_units_by_weights(amount_units, line_weights, min_units=1)
            line_vals = []
            try:
                for candidate, line_units in zip(prepared_candidates, line_amount_units):
                    line_total = self._units_to_amount(line_units)
                    line_vals.append(
                        self._build_line_vals_for_product(
                            line_total,
                            partner,
                            candidate["product"],
                            fiscal_position,
                            candidate["qty"],
                        )
                    )
            except ValidationError:
                continue
            return line_vals, fiscal_position

        raise UserError(
            _(
                "Unable to build a realistic basket for ticket amount %(amount)s. "
                "Review the selected POS categories, product rules, or ticket range.",
                amount=amount_total,
            )
        )

    def _prepare_transaction_vals(
        self,
        date_order,
        amount_total,
        customers,
        product_candidates,
        payment_candidates,
        previous_partner_id=False,
    ):
        self.ensure_one()
        partner = self._pick_customer(customers, previous_partner_id=previous_partner_id)
        payment_candidate = self._weighted_choice(payment_candidates)
        payment_method = payment_candidate["payment_method"]
        line_vals, fiscal_position = self._build_transaction_lines(amount_total, partner, product_candidates)

        return {
            "batch_id": self.id,
            "date_order": date_order,
            "partner_id": partner.id,
            "user_id": self.user_id.id,
            "config_id": self.pos_config_id.id,
            "pricelist_id": self.pricelist_id.id,
            "fiscal_position_id": fiscal_position.id if fiscal_position else False,
            "line_ids": [Command.create(line_val) for line_val in line_vals],
            "payment_ids": [
                Command.create(
                    {
                        "payment_date": date_order,
                        "payment_method_id": payment_method.id,
                        "amount": amount_total,
                    }
                )
            ],
        }, partner.id

    def action_generate_transactions(self):
        for simulation in self:
            simulation._validate_generation_inputs()
            customers = simulation._get_customer_pool()
            product_candidates = simulation._get_product_candidates()
            payment_candidates = simulation._get_payment_candidates()
            datetimes = simulation._generate_timestamps()
            amounts = simulation._distribute_amounts()

            simulation.transaction_ids.unlink()
            previous_partner_id = False
            transaction_values = []
            for date_order, amount_total in zip(datetimes, amounts):
                transaction_val, previous_partner_id = simulation._prepare_transaction_vals(
                    date_order,
                    amount_total,
                    customers,
                    product_candidates,
                    payment_candidates,
                    previous_partner_id=previous_partner_id,
                )
                transaction_values.append(transaction_val)

            self.env["pos.sales.simulation.transaction"].create(transaction_values)
            simulation.write(
                {
                    "state": "done",
                    "generated_at": fields.Datetime.now(),
                }
            )
            simulation.invalidate_recordset(
                ["transaction_ids", "transaction_count_generated", "total_revenue_actual", "revenue_gap"]
            )
        return True

    def action_view_transactions(self):
        self.ensure_one()
        action = self.env.ref("pos_sales_simulation.action_pos_sales_simulation_transaction").read()[0]
        action["domain"] = [("batch_id", "=", self.id)]
        action["context"] = {"default_batch_id": self.id}
        return action

    def action_print_pdf(self):
        self.ensure_one()
        return self.env.ref("pos_sales_simulation.action_report_pos_sales_simulation").report_action(self)

    def action_download_excel(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/pos_sales_simulation/{self.id}/xlsx",
            "target": "self",
        }

    def _build_xlsx_file(self):
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        header_style = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        number_style = workbook.add_format({"num_format": "#,##0.00", "border": 1})
        text_style = workbook.add_format({"border": 1})
        title_style = workbook.add_format({"bold": True, "font_size": 14})

        worksheet = workbook.add_worksheet(_("Transactions")[:31])
        worksheet.set_column("A:A", 20)
        worksheet.set_column("B:B", 22)
        worksheet.set_column("C:D", 20)
        worksheet.set_column("E:E", 24)
        worksheet.set_column("F:H", 16)

        row = 0
        worksheet.write(row, 0, self.name, title_style)
        row += 2
        worksheet.write(row, 0, _("Point of Sale"), header_style)
        worksheet.write(row, 1, self.pos_config_id.display_name or "", text_style)
        row += 1
        worksheet.write(row, 0, _("Period"), header_style)
        worksheet.write(row, 1, f"{self.date_from} - {self.date_to}", text_style)
        row += 1
        worksheet.write(row, 0, _("Opening Hours"), header_style)
        worksheet.write(row, 1, f"{self._format_hour(self.opening_hour)} - {self._format_hour(self.closing_hour)}", text_style)
        row += 1
        worksheet.write(row, 0, _("Target Revenue"), header_style)
        worksheet.write_number(row, 1, self.target_revenue, number_style)
        row += 1
        worksheet.write(row, 0, _("Actual Revenue"), header_style)
        worksheet.write_number(row, 1, self.total_revenue_actual, number_style)
        row += 2

        headers = [
            _("Reference"),
            _("Transaction Date"),
            _("Customer"),
            _("Salesperson"),
            _("Payment Method"),
            _("Untaxed"),
            _("Tax"),
            _("Total"),
        ]
        for column, header in enumerate(headers):
            worksheet.write(row, column, header, header_style)
        row += 1

        for transaction in self.transaction_ids.sorted("date_order"):
            local_date = fields.Datetime.context_timestamp(self, transaction.date_order)
            worksheet.write(row, 0, transaction.name, text_style)
            worksheet.write(row, 1, local_date.strftime("%Y-%m-%d %H:%M:%S"), text_style)
            worksheet.write(row, 2, transaction.partner_id.display_name or "", text_style)
            worksheet.write(row, 3, transaction.user_id.display_name or "", text_style)
            worksheet.write(row, 4, transaction.payment_method_summary or "", text_style)
            worksheet.write_number(row, 5, transaction.amount_untaxed, number_style)
            worksheet.write_number(row, 6, transaction.amount_tax, number_style)
            worksheet.write_number(row, 7, transaction.amount_total, number_style)
            row += 1

        workbook.close()
        filename = f"{self.name.replace('/', '_')}.xlsx"
        return output.getvalue(), filename


class PosSalesSimulationTransaction(models.Model):
    _name = "pos.sales.simulation.transaction"
    _description = "POS Sales Simulation Transaction"
    _order = "date_order desc, name desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Transaction Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    batch_id = fields.Many2one(
        "pos.sales.simulation",
        string="Batch",
        required=True,
        ondelete="cascade",
        index=True,
        check_company=True,
    )
    state = fields.Selection(
        [("done", "Done")],
        default="done",
        required=True,
        readonly=True,
    )
    date_order = fields.Datetime(required=True, index=True)
    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Salesperson",
        required=True,
    )
    config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="config_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="config_id.currency_id",
        store=True,
        readonly=True,
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Pricelist",
        required=True,
        check_company=True,
    )
    fiscal_position_id = fields.Many2one(
        "account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
    )
    line_ids = fields.One2many(
        "pos.sales.simulation.transaction.line",
        "transaction_id",
        string="Transaction Lines",
    )
    payment_ids = fields.One2many(
        "pos.sales.simulation.payment",
        "transaction_id",
        string="Payments",
    )
    amount_untaxed = fields.Monetary(
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_tax = fields.Monetary(
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    amount_total = fields.Monetary(
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    payment_total = fields.Monetary(
        compute="_compute_amounts",
        currency_field="currency_id",
        store=True,
    )
    payment_method_summary = fields.Char(
        compute="_compute_payment_method_summary",
        string="Payment Method",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("pos.sales.simulation.transaction") or _("New")
        return super().create(vals_list)

    @api.depends(
        "line_ids.price_subtotal",
        "line_ids.price_subtotal_incl",
        "payment_ids.amount",
    )
    def _compute_amounts(self):
        for transaction in self:
            untaxed = sum(transaction.line_ids.mapped("price_subtotal"))
            total = sum(transaction.line_ids.mapped("price_subtotal_incl"))
            transaction.amount_untaxed = transaction.currency_id.round(untaxed)
            transaction.amount_total = transaction.currency_id.round(total)
            transaction.amount_tax = transaction.currency_id.round(transaction.amount_total - transaction.amount_untaxed)
            transaction.payment_total = transaction.currency_id.round(sum(transaction.payment_ids.mapped("amount")))

    @api.depends("payment_ids.payment_method_id")
    def _compute_payment_method_summary(self):
        for transaction in self:
            transaction.payment_method_summary = ", ".join(
                transaction.payment_ids.mapped("payment_method_id.name")
            )


class PosSalesSimulationTransactionLine(models.Model):
    _name = "pos.sales.simulation.transaction.line"
    _description = "POS Sales Simulation Transaction Line"
    _order = "sequence, id"
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    transaction_id = fields.Many2one(
        "pos.sales.simulation.transaction",
        string="Transaction Ref",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="transaction_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="transaction_id.currency_id",
        store=True,
        readonly=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain=[("sale_ok", "=", True)],
    )
    full_product_name = fields.Char(string="Description")
    qty = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure",
        default=1.0,
        required=True,
    )
    price_unit = fields.Float(string="Unit Price", digits=0, required=True)
    discount = fields.Float(string="Discount (%)", digits=0, default=0.0)
    tax_ids = fields.Many2many("account.tax", string="Taxes")
    tax_ids_after_fiscal_position = fields.Many2many(
        "account.tax",
        compute="_compute_tax_ids_after_fiscal_position",
        string="Applied Taxes",
    )
    price_subtotal = fields.Monetary(
        string="Subtotal w/o Tax",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    price_subtotal_incl = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    @api.depends("tax_ids", "transaction_id.fiscal_position_id")
    def _compute_tax_ids_after_fiscal_position(self):
        for line in self:
            if line.transaction_id.fiscal_position_id:
                line.tax_ids_after_fiscal_position = line.transaction_id.fiscal_position_id.map_tax(line.tax_ids)
            else:
                line.tax_ids_after_fiscal_position = line.tax_ids

    @api.depends(
        "qty",
        "price_unit",
        "discount",
        "tax_ids",
        "transaction_id.fiscal_position_id",
        "transaction_id.partner_id",
    )
    def _compute_amounts(self):
        for line in self:
            discounted_price = line.price_unit * (1 - ((line.discount or 0.0) / 100.0))
            mapped_taxes = (
                line.transaction_id.fiscal_position_id.map_tax(line.tax_ids)
                if line.transaction_id.fiscal_position_id
                else line.tax_ids
            )
            if mapped_taxes:
                tax_result = mapped_taxes.compute_all(
                    discounted_price,
                    line.currency_id,
                    line.qty,
                    product=line.product_id,
                    partner=line.transaction_id.partner_id,
                )
                line.price_subtotal = line.currency_id.round(tax_result["total_excluded"])
                line.price_subtotal_incl = line.currency_id.round(tax_result["total_included"])
            else:
                line.price_subtotal = line.currency_id.round(discounted_price * line.qty)
                line.price_subtotal_incl = line.currency_id.round(discounted_price * line.qty)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id or not self.transaction_id:
            return
        taxes = self.product_id.taxes_id.filtered_domain(
            self.env["account.tax"]._check_company_domain(self.transaction_id.company_id)
        )
        mapped_taxes = (
            self.transaction_id.fiscal_position_id.map_tax(taxes)
            if self.transaction_id.fiscal_position_id
            else taxes
        )
        price = self.transaction_id.pricelist_id._get_product_price(
            self.product_id,
            self.qty or 1.0,
            currency=self.currency_id,
        )
        self.tax_ids = taxes
        self.price_unit = self.env["account.tax"]._fix_tax_included_price_company(
            price,
            taxes,
            mapped_taxes,
            self.transaction_id.company_id,
        )
        self.full_product_name = self.product_id.display_name


class PosSalesSimulationPayment(models.Model):
    _name = "pos.sales.simulation.payment"
    _description = "POS Sales Simulation Payment"
    _order = "payment_date desc, id desc"
    _check_company_auto = True

    name = fields.Char(
        string="Payment Reference",
        required=True,
        copy=False,
        default=lambda self: _("New"),
    )
    transaction_id = fields.Many2one(
        "pos.sales.simulation.transaction",
        string="Transaction Ref",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="transaction_id.company_id",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="transaction_id.currency_id",
        store=True,
        readonly=True,
    )
    payment_date = fields.Datetime(required=True, default=fields.Datetime.now)
    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Payment Method",
        required=True,
        check_company=True,
    )
    amount = fields.Monetary(required=True, currency_field="currency_id")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("pos.sales.simulation.payment") or _("New")
        return super().create(vals_list)

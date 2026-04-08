import io
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
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="pos_config_id.company_id",
        store=True,
        readonly=True,
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
    target_revenue = fields.Monetary(required=True, currency_field="currency_id")
    transaction_count = fields.Integer(required=True, default=10)
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
    customer_ids = fields.Many2many(
        "res.partner",
        "pos_sales_simulation_partner_rel",
        "simulation_id",
        "partner_id",
        string="Customer Source",
        help="Optional customer pool used when generating simulation transactions.",
    )
    product_ids = fields.Many2many(
        "product.product",
        "pos_sales_simulation_product_rel",
        "simulation_id",
        "product_id",
        string="Product Source",
        help="Optional product pool used when generating simulation transactions.",
    )
    payment_method_ids = fields.Many2many(
        "pos.payment.method",
        "pos_sales_simulation_payment_method_rel",
        "simulation_id",
        "payment_method_id",
        string="Payment Method Source",
        help="Optional payment method pool used when generating simulation transactions.",
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

    @api.depends("target_revenue", "transaction_ids.amount_total")
    def _compute_summary_fields(self):
        for simulation in self:
            simulation.transaction_count_generated = len(simulation.transaction_ids)
            simulation.total_revenue_actual = sum(simulation.transaction_ids.mapped("amount_total"))
            simulation.revenue_gap = simulation.target_revenue - simulation.total_revenue_actual

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code("pos.sales.simulation") or _("New")
            if vals.get("pos_config_id"):
                config = self.env["pos.config"].browse(vals["pos_config_id"])
                vals.setdefault("opening_hour", config.simulation_opening_hour)
                vals.setdefault("closing_hour", config.simulation_closing_hour)
                default_pricelist = self._get_default_pricelist(config)
                if default_pricelist:
                    vals.setdefault("pricelist_id", default_pricelist.id)
                vals.setdefault(
                    "payment_method_ids",
                    [Command.set(config.payment_method_ids.ids)],
                )
        return super().create(vals_list)

    @api.onchange("pos_config_id")
    def _onchange_pos_config_id(self):
        if not self.pos_config_id:
            return
        self.opening_hour = self.pos_config_id.simulation_opening_hour
        self.closing_hour = self.pos_config_id.simulation_closing_hour
        default_pricelist = self._get_default_pricelist(self.pos_config_id)
        if default_pricelist:
            self.pricelist_id = default_pricelist
        self.payment_method_ids = self.pos_config_id.payment_method_ids

    @api.constrains(
        "date_from",
        "date_to",
        "opening_hour",
        "closing_hour",
        "transaction_count",
        "target_revenue",
        "min_transaction_amount",
        "max_transaction_amount",
    )
    def _check_simulation_constraints(self):
        for simulation in self:
            simulation._validate_generation_inputs()

    def _validate_generation_inputs(self):
        for simulation in self:
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
            if simulation.transaction_count <= 0:
                raise ValidationError(_("Transaction count must be greater than zero."))
            if simulation.target_revenue <= 0:
                raise ValidationError(_("Target revenue must be greater than zero."))
            if simulation.min_transaction_amount <= 0 or simulation.max_transaction_amount <= 0:
                raise ValidationError(_("Minimum and maximum ticket amounts must be greater than zero."))
            if simulation.min_transaction_amount > simulation.max_transaction_amount:
                raise ValidationError(_("Minimum ticket amount must not exceed the maximum ticket amount."))

            total_units = simulation._amount_to_units(simulation.target_revenue)
            min_units = simulation._amount_to_units(simulation.min_transaction_amount)
            max_units = simulation._amount_to_units(simulation.max_transaction_amount)
            min_total = min_units * simulation.transaction_count
            max_total = max_units * simulation.transaction_count
            if total_units < min_total or total_units > max_total:
                minimum_amount = simulation._units_to_amount(min_total)
                maximum_amount = simulation._units_to_amount(max_total)
                raise ValidationError(
                    _(
                        "Target revenue must fit the ticket range for the requested transaction count.\n"
                        "Allowed range: %(minimum)s to %(maximum)s.",
                        minimum=minimum_amount,
                        maximum=maximum_amount,
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

    def _get_customer_pool(self):
        self.ensure_one()
        if self.customer_ids:
            return self.customer_ids
        partners = self.env["res.partner"].search(
            [
                ("active", "=", True),
                ("customer_rank", ">", 0),
            ]
        )
        if not partners:
            partners = self.env["res.partner"].search(
                [
                    ("active", "=", True),
                    ("type", "!=", "private"),
                ]
            )
        if not partners:
            raise UserError(_("No customer is available for the simulation."))
        return partners

    def _get_product_pool(self):
        self.ensure_one()
        if self.product_ids:
            return self.product_ids
        products = self.env["product.product"].search(
            [
                ("active", "=", True),
                ("sale_ok", "=", True),
                ("product_tmpl_id.available_in_pos", "=", True),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.company_id.id),
            ]
        )
        if not products:
            raise UserError(_("No POS product is available for the simulation."))
        return products

    def _get_payment_method_pool(self):
        self.ensure_one()
        payment_methods = self.payment_method_ids or self.pos_config_id.payment_method_ids
        if not payment_methods:
            raise UserError(_("No payment method is configured for this point of sale."))
        return payment_methods

    def _get_local_timezone(self):
        tz_name = self.env.user.tz or self.env.context.get("tz") or "UTC"
        return pytz.timezone(tz_name)

    def _generate_timestamps(self):
        self.ensure_one()
        tz = self._get_local_timezone()
        start_date = fields.Date.to_date(self.date_from)
        end_date = fields.Date.to_date(self.date_to)
        day_count = (end_date - start_date).days + 1
        opening_second = int(self.opening_hour * 3600)
        closing_second = min(int(self.closing_hour * 3600) - 1, 86399)
        if closing_second < opening_second:
            closing_second = opening_second

        datetimes = []
        for _index in range(self.transaction_count):
            selected_date = start_date + timedelta(days=random.randint(0, day_count - 1))
            selected_second = random.randint(opening_second, closing_second)
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
        total_units = self._amount_to_units(self.target_revenue)
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

    def _build_line_vals(self, target_total, partner, product_pool):
        self.ensure_one()
        for _attempt in range(60):
            product = random.choice(product_pool)
            taxes = self._get_company_taxes(product)
            fiscal_position = self._get_fiscal_position(partner)
            mapped_taxes = fiscal_position.map_tax(taxes) if fiscal_position else taxes
            quantity = random.randint(1, 3)
            discount = random.choice([0.0, 0.0, 0.0, 5.0, 10.0])
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
            }, fiscal_position

        raise UserError(
            _(
                "Unable to generate a transaction line that matches ticket amount %(amount)s. "
                "Review the selected products or ticket range.",
                amount=target_total,
            )
        )

    def _prepare_transaction_vals(self, date_order, amount_total, customers, products, payment_methods):
        self.ensure_one()
        partner = random.choice(customers)
        payment_method = random.choice(payment_methods)
        line_vals, fiscal_position = self._build_line_vals(amount_total, partner, products)

        return {
            "batch_id": self.id,
            "date_order": date_order,
            "partner_id": partner.id,
            "user_id": self.user_id.id,
            "config_id": self.pos_config_id.id,
            "pricelist_id": self.pricelist_id.id,
            "fiscal_position_id": fiscal_position.id if fiscal_position else False,
            "line_ids": [Command.create(line_vals)],
            "payment_ids": [
                Command.create(
                    {
                        "payment_date": date_order,
                        "payment_method_id": payment_method.id,
                        "amount": amount_total,
                    }
                )
            ],
        }

    def action_generate_transactions(self):
        for simulation in self:
            simulation._validate_generation_inputs()
            customers = simulation._get_customer_pool()
            products = simulation._get_product_pool()
            payment_methods = simulation._get_payment_method_pool()
            datetimes = simulation._generate_timestamps()
            amounts = simulation._distribute_amounts()

            simulation.transaction_ids.unlink()
            transaction_values = [
                simulation._prepare_transaction_vals(date_order, amount_total, customers, products, payment_methods)
                for date_order, amount_total in zip(datetimes, amounts)
            ]
            self.env["pos.sales.simulation.transaction"].create(transaction_values)
            simulation.write(
                {
                    "state": "done",
                    "generated_at": fields.Datetime.now(),
                }
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
        worksheet.write(row, 1, f"{self.opening_hour:0.2f} - {self.closing_hour:0.2f}", text_style)
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
            transaction.amount_untaxed = untaxed
            transaction.amount_total = total
            transaction.amount_tax = total - untaxed
            transaction.payment_total = sum(transaction.payment_ids.mapped("amount"))

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
                line.price_subtotal = tax_result["total_excluded"]
                line.price_subtotal_incl = tax_result["total_included"]
            else:
                line.price_subtotal = discounted_price * line.qty
                line.price_subtotal_incl = discounted_price * line.qty

    @api.onchange("product_id")
    def _onchange_product_id(self):
        if not self.product_id or not self.transaction_id:
            return
        taxes = self.product_id.taxes_id.filtered_domain(
            self.env["account.tax"]._check_company_domain(self.transaction_id.company_id)
        )
        mapped_taxes = self.transaction_id.fiscal_position_id.map_tax(taxes) if self.transaction_id.fiscal_position_id else taxes
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

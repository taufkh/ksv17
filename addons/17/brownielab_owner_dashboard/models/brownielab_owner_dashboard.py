from datetime import date, timedelta
import html

from odoo import _, api, fields, models
from odoo.tools import format_date


class BrownielabOwnerDashboard(models.Model):
    _name = "brownielab.owner.dashboard"
    _description = "Brownielab Owner Dashboard"

    name = fields.Char(default="Owner Dashboard", required=True)
    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", store=True, readonly=True)

    filter_mode = fields.Selection(
        [
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("year", "Year"),
            ("custom", "Custom Range"),
        ],
        default="custom",
        required=True,
    )
    date_from = fields.Date(default=lambda self: fields.Date.start_of(fields.Date.context_today(self), "month"))
    date_to = fields.Date(default=lambda self: fields.Date.context_today(self))
    selected_day = fields.Date(default=lambda self: fields.Date.context_today(self))
    selected_week = fields.Date(default=lambda self: self._default_selected_week())
    selected_month = fields.Date(default=lambda self: self._default_selected_month())
    selected_year = fields.Integer(default=lambda self: fields.Date.context_today(self).year)
    selected_week_key = fields.Selection(selection="_selection_weeks", default=lambda self: self._default_selected_week_key())
    selected_month_key = fields.Selection(selection="_selection_months", default=lambda self: self._default_selected_month_key())
    selected_year_key = fields.Selection(selection="_selection_years", default=lambda self: self._default_selected_year_key())

    effective_date_from = fields.Date(readonly=True)
    effective_date_to = fields.Date(readonly=True)
    filter_note = fields.Char(readonly=True)

    omzet_daily = fields.Monetary(readonly=True)
    omzet_today = fields.Monetary(readonly=True)
    omzet_weekly = fields.Monetary(readonly=True)
    omzet_monthly = fields.Monetary(readonly=True)
    omzet_yearly = fields.Monetary(readonly=True)
    cash_out_daily = fields.Monetary(readonly=True)
    cash_out_weekly = fields.Monetary(readonly=True)
    cash_out_monthly = fields.Monetary(readonly=True)
    cash_out_yearly = fields.Monetary(readonly=True)

    vendor_bills_due_amount = fields.Monetary(readonly=True)
    vendor_bills_due_count = fields.Integer(readonly=True)
    vendor_bills_outstanding_amount = fields.Monetary(readonly=True)
    vendor_bills_outstanding_count = fields.Integer(readonly=True)
    unreconciled_bills_amount = fields.Monetary(readonly=True)
    unreconciled_bills_count = fields.Integer(readonly=True)

    saldo_ocbc = fields.Monetary(readonly=True)
    saldo_bca = fields.Monetary(readonly=True)

    chart_html = fields.Html(readonly=True, sanitize=False)
    vendor_bills_html = fields.Html(readonly=True, sanitize=False)
    unreconciled_bills_html = fields.Html(readonly=True, sanitize=False)
    filter_summary_html = fields.Html(readonly=True, sanitize=False)
    ocbc_card_html = fields.Html(readonly=True, sanitize=False)
    bca_card_html = fields.Html(readonly=True, sanitize=False)

    _sql_constraints = [
        (
            "brownielab_owner_dashboard_user_company_unique",
            "unique(user_id, company_id)",
            "Only one owner dashboard is allowed per user and company.",
        )
    ]

    @api.model
    def _default_selected_week(self):
        today = fields.Date.context_today(self)
        return today - timedelta(days=today.weekday())

    @api.model
    def _default_selected_month(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    @api.model
    def _default_selected_week_key(self):
        today = fields.Date.context_today(self)
        iso_year, iso_week, _iso_weekday = today.isocalendar()
        return f"{iso_year}-W{iso_week:02d}"

    @api.model
    def _default_selected_month_key(self):
        today = fields.Date.context_today(self)
        return f"{today.year:04d}-{today.month:02d}"

    @api.model
    def _default_selected_year_key(self):
        return str(fields.Date.context_today(self).year)

    @api.model
    def _selection_weeks(self):
        today = fields.Date.context_today(self)
        current_monday = today - timedelta(days=today.weekday())
        options = []
        for offset in range(-12, 13):
            week_start = current_monday + timedelta(weeks=offset)
            iso_year, iso_week, _iso_weekday = week_start.isocalendar()
            week_end = week_start + timedelta(days=6)
            key = f"{iso_year}-W{iso_week:02d}"
            label = _("Week %s, %s (%s - %s)") % (
                f"{iso_week:02d}",
                iso_year,
                format_date(self.env, week_start),
                format_date(self.env, week_end),
            )
            options.append((key, label))
        return options

    @api.model
    def _selection_months(self):
        today = fields.Date.context_today(self)
        month_anchor = today.replace(day=1)
        options = []
        for offset in range(-12, 13):
            year_value = month_anchor.year + ((month_anchor.month - 1 + offset) // 12)
            month_value = ((month_anchor.month - 1 + offset) % 12) + 1
            month_start = date(year_value, month_value, 1)
            key = f"{year_value:04d}-{month_value:02d}"
            label = format_date(self.env, month_start, date_format="MMMM yyyy")
            options.append((key, label))
        return options

    @api.model
    def _selection_years(self):
        current_year = fields.Date.context_today(self).year
        return [(str(year_value), str(year_value)) for year_value in range(current_year - 5, current_year + 3)]

    @api.model
    def action_open_dashboard(self):
        user = self.env.user
        company = self.env.company
        dashboard = self.search(
            [("user_id", "=", user.id), ("company_id", "=", company.id)],
            limit=1,
        )
        if not dashboard:
            dashboard = self.create(
                {
                    "user_id": user.id,
                    "company_id": company.id,
                }
            )
        dashboard._recompute_dashboard()
        return {
            "type": "ir.actions.act_window",
            "name": _("Owner Dashboard"),
            "res_model": "brownielab.owner.dashboard",
            "view_mode": "form",
            "views": [(self.env.ref("brownielab_owner_dashboard.view_brownielab_owner_dashboard_form").id, "form")],
            "res_id": dashboard.id,
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_dashboard()
        return records

    def write(self, vals):
        result = super().write(vals)
        if not self.env.context.get("skip_dashboard_recompute") and set(vals) & self._dashboard_filter_fields():
            self._recompute_dashboard()
        return result

    @api.model
    def _dashboard_filter_fields(self):
        return {
            "filter_mode",
            "date_from",
            "date_to",
            "selected_day",
            "selected_week",
            "selected_month",
            "selected_year",
            "selected_week_key",
            "selected_month_key",
            "selected_year_key",
        }

    def action_apply_filter(self):
        self.ensure_one()
        self._recompute_dashboard()
        return self.action_open_dashboard()

    def action_reset_filter(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        self.with_context(skip_dashboard_recompute=True).write(
            {
                "filter_mode": "custom",
                "date_from": today.replace(day=1),
                "date_to": today,
                "selected_day": today,
                "selected_week": today - timedelta(days=today.weekday()),
                "selected_month": today.replace(day=1),
                "selected_year": today.year,
                "selected_week_key": self._default_selected_week_key(),
                "selected_month_key": self._default_selected_month_key(),
                "selected_year_key": self._default_selected_year_key(),
            }
        )
        self._recompute_dashboard()
        return self.action_open_dashboard()

    def _recompute_dashboard(self):
        for record in self:
            date_start, date_end = record._get_effective_range()
            today_start, today_end = record._get_today_range()
            daily_start, daily_end = record._get_day_range()
            weekly_start, weekly_end = record._get_week_range()
            monthly_start, monthly_end = record._get_month_range()
            yearly_start, yearly_end = record._get_year_range()

            values = {
                "effective_date_from": date_start,
                "effective_date_to": date_end,
                "filter_note": _("All metrics follow the selected period."),
                "selected_week_key": record.selected_week_key or record._default_selected_week_key(),
                "selected_month_key": record.selected_month_key or record._default_selected_month_key(),
                "selected_year_key": record.selected_year_key or record._default_selected_year_key(),
                "omzet_daily": record._get_revenue_amount(daily_start, daily_end),
                "omzet_today": record._get_revenue_amount(today_start, today_end),
                "omzet_weekly": record._get_revenue_amount(weekly_start, weekly_end),
                "omzet_monthly": record._get_revenue_amount(monthly_start, monthly_end),
                "omzet_yearly": record._get_revenue_amount(yearly_start, yearly_end),
                "cash_out_daily": record._get_cash_out_amount(daily_start, daily_end),
                "cash_out_weekly": record._get_cash_out_amount(weekly_start, weekly_end),
                "cash_out_monthly": record._get_cash_out_amount(monthly_start, monthly_end),
                "cash_out_yearly": record._get_cash_out_amount(yearly_start, yearly_end),
            }

            due_bills = record._get_due_vendor_bills(date_start, date_end)
            outstanding_bills = record._get_outstanding_vendor_bills(date_end)
            unreconciled_bills = record._get_unreconciled_vendor_bills(date_end)
            due_amount = sum(abs(bill.amount_residual) for bill in due_bills)
            outstanding_amount = sum(abs(bill.amount_residual) for bill in outstanding_bills)
            unreconciled_amount = sum(abs(bill.amount_total) for bill in unreconciled_bills)
            values.update(
                {
                    "vendor_bills_due_amount": due_amount,
                    "vendor_bills_due_count": len(due_bills),
                    "vendor_bills_outstanding_amount": outstanding_amount,
                    "vendor_bills_outstanding_count": len(outstanding_bills),
                    "unreconciled_bills_amount": unreconciled_amount,
                    "unreconciled_bills_count": len(unreconciled_bills),
                }
            )

            ocbc_journal = record._find_bank_journal("ocbc")
            bca_journal = record._find_bank_journal("bca")
            values["saldo_ocbc"] = record._get_journal_balance(ocbc_journal, date_end)
            values["saldo_bca"] = record._get_journal_balance(bca_journal, date_end)
            values["chart_html"] = record._build_chart_html(date_start, date_end)
            values["vendor_bills_html"] = record._build_vendor_bills_html(due_bills)
            values["unreconciled_bills_html"] = record._build_unreconciled_bills_html(unreconciled_bills)
            values["filter_summary_html"] = record._build_filter_summary_html(date_start, date_end, due_bills, due_amount)
            values["ocbc_card_html"] = record._build_bank_card_html(ocbc_journal, values["saldo_ocbc"], date_start, date_end)
            values["bca_card_html"] = record._build_bank_card_html(bca_journal, values["saldo_bca"], date_start, date_end)
            record.with_context(skip_dashboard_recompute=True).write(values)

    def _get_effective_range(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if self.filter_mode == "day":
            day = self.selected_day or today
            return day, day
        if self.filter_mode == "week":
            week_start = self._get_selected_week_start()
            return week_start, week_start + timedelta(days=6)
        if self.filter_mode == "month":
            month_start = self._get_selected_month_start()
            month_end = fields.Date.end_of(month_start, "month")
            return month_start, month_end
        if self.filter_mode == "year":
            year_value = self._get_selected_year_value()
            year_start = date(year_value, 1, 1)
            year_end = date(year_value, 12, 31)
            return year_start, year_end
        date_start = self.date_from or today.replace(day=1)
        date_end = self.date_to or today
        if date_end < date_start:
            date_start, date_end = date_end, date_start
        return date_start, date_end

    def _get_day_range(self):
        anchor = self.selected_day or self.effective_date_to or fields.Date.context_today(self)
        return anchor, anchor

    def _get_today_range(self):
        today = fields.Date.context_today(self)
        return today, today

    def _get_week_range(self):
        start = self._get_selected_week_start()
        return start, start + timedelta(days=6)

    def _get_month_range(self):
        start = self._get_selected_month_start()
        return start, fields.Date.end_of(start, "month")

    def _get_year_range(self):
        year_value = self._get_selected_year_value()
        return date(year_value, 1, 1), date(year_value, 12, 31)

    def _get_selected_week_start(self):
        self.ensure_one()
        if self.selected_week_key:
            year_part, week_part = self.selected_week_key.split("-W")
            return date.fromisocalendar(int(year_part), int(week_part), 1)
        anchor = self.selected_week or self.effective_date_to or fields.Date.context_today(self)
        return anchor - timedelta(days=anchor.weekday())

    def _get_selected_month_start(self):
        self.ensure_one()
        if self.selected_month_key:
            year_part, month_part = self.selected_month_key.split("-")
            return date(int(year_part), int(month_part), 1)
        anchor = self.selected_month or self.effective_date_to or fields.Date.context_today(self)
        return anchor.replace(day=1)

    def _get_selected_year_value(self):
        self.ensure_one()
        if self.selected_year_key:
            return int(self.selected_year_key)
        return self.selected_year or (self.effective_date_to or fields.Date.context_today(self)).year

    def _get_revenue_amount(self, date_start, date_end):
        return self._get_pos_revenue_amount(date_start, date_end) + self._get_invoice_revenue_amount(date_start, date_end)

    @api.model
    def _read_group_sum(self, grouped_data, preferred_keys):
        if not grouped_data:
            return 0.0
        row = grouped_data[0]
        for key in preferred_keys:
            if key in row and row[key] is not None:
                return row[key]
        for key, value in row.items():
            if key == "__count":
                continue
            if key.endswith("_sum") and value is not None:
                return value
        return 0.0

    def _get_pos_revenue_amount(self, date_start, date_end):
        pos_data = self.env["pos.order"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "in", ["paid", "done", "invoiced"]),
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<", fields.Datetime.to_string(date_end + timedelta(days=1))),
            ],
            ["amount_total:sum"],
            [],
        )
        return self._read_group_sum(pos_data, ["amount_total", "amount_total_sum"])

    def _get_invoice_revenue_amount(self, date_start, date_end):
        move_data = self.env["account.move"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "in", ["out_invoice", "out_refund", "out_receipt"]),
                ("invoice_date", ">=", date_start),
                ("invoice_date", "<=", date_end),
                "|",
                ("invoice_origin", "=", False),
                ("invoice_origin", "not ilike", "POS%"),
            ],
            ["amount_total_signed:sum"],
            [],
        )
        return self._read_group_sum(move_data, ["amount_total_signed", "amount_total_signed_sum"])

    def _get_cash_out_amount(self, date_start, date_end):
        payment_data = self.env["account.payment"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("payment_type", "=", "outbound"),
                ("date", ">=", date_start),
                ("date", "<=", date_end),
            ],
            ["amount:sum"],
            [],
        )
        return self._read_group_sum(payment_data, ["amount", "amount_sum"])

    def _get_due_vendor_bills(self, date_start, date_end):
        return self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "=", "in_invoice"),
                ("payment_state", "in", ["not_paid", "partial", "in_payment"]),
                ("amount_residual", ">", 0),
                ("invoice_date_due", ">=", date_start),
                ("invoice_date_due", "<=", date_end),
            ],
            order="invoice_date_due asc, name asc",
        )

    def _get_outstanding_vendor_bills(self, cutoff_date):
        return self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "=", "in_invoice"),
                ("payment_state", "in", ["not_paid", "partial", "in_payment"]),
                ("amount_residual", ">", 0),
                ("invoice_date", "<=", cutoff_date),
            ]
        )

    def _get_unreconciled_vendor_bills(self, cutoff_date):
        return self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("state", "=", "posted"),
                ("move_type", "=", "in_invoice"),
                ("payment_state", "=", "in_payment"),
                ("invoice_date", "<=", cutoff_date),
            ],
            order="invoice_date_due asc, name asc",
        )

    def _find_bank_journal(self, keyword):
        return self.env["account.journal"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type", "=", "bank"),
                "|",
                "|",
                ("name", "ilike", keyword),
                ("code", "ilike", keyword),
                ("bank_acc_number", "ilike", keyword),
            ],
            limit=1,
        )

    def _get_journal_balance(self, journal, cutoff_date):
        if not journal or not journal.default_account_id:
            return 0.0
        aml_data = self.env["account.move.line"].read_group(
            [
                ("company_id", "=", self.company_id.id),
                ("parent_state", "=", "posted"),
                ("account_id", "=", journal.default_account_id.id),
                ("date", "<=", cutoff_date),
            ],
            ["balance:sum"],
            [],
        )
        return self._read_group_sum(aml_data, ["balance", "balance_sum"])

    def _build_chart_html(self, date_start, date_end):
        labels, omzet_series, cash_out_series = self._get_chart_series(date_start, date_end)
        chart_svg = self._build_dual_line_svg(labels, {"Omzet": omzet_series, "Cash Out": cash_out_series})
        return f"""
            <div class="o_brownie_chart_card">
                <div class="o_brownie_section_head">
                    <div>
                        <h3>Tren Omset &amp; Cash Out</h3>
                        <span>{html.escape(self._describe_range(date_start, date_end))}</span>
                    </div>
                    <div class="o_brownie_legend">
                        <span class="is-omzet">Omset</span>
                        <span class="is-cashout">Cash Out</span>
                    </div>
                </div>
                {chart_svg}
            </div>
        """

    def _get_chart_series(self, date_start, date_end):
        total_days = (date_end - date_start).days + 1
        if total_days <= 14:
            step = "day"
        elif total_days <= 90:
            step = "week"
        else:
            step = "month"
        labels = []
        omzet_values = []
        cash_values = []
        cursor = date_start
        while cursor <= date_end:
            if step == "day":
                bucket_start = cursor
                bucket_end = cursor
                next_cursor = cursor + timedelta(days=1)
                label = format_date(self.env, cursor, date_format="dd MMM")
            elif step == "week":
                bucket_start = cursor
                bucket_end = min(cursor + timedelta(days=6), date_end)
                next_cursor = bucket_end + timedelta(days=1)
                label = f"{format_date(self.env, bucket_start, date_format='dd MMM')} - {format_date(self.env, bucket_end, date_format='dd MMM')}"
            else:
                bucket_start = cursor.replace(day=1)
                bucket_end = min(fields.Date.end_of(bucket_start, "month"), date_end)
                next_cursor = bucket_end + timedelta(days=1)
                label = format_date(self.env, bucket_start, date_format="MMM yyyy")
            labels.append(label)
            omzet_values.append(self._get_revenue_amount(bucket_start, bucket_end))
            cash_values.append(self._get_cash_out_amount(bucket_start, bucket_end))
            cursor = next_cursor
        return labels, omzet_values, cash_values

    def _build_dual_line_svg(self, labels, series_map):
        width = 860
        height = 260
        padding_left = 36
        padding_right = 14
        padding_top = 18
        padding_bottom = 42
        chart_width = width - padding_left - padding_right
        chart_height = height - padding_top - padding_bottom
        max_value = max([1.0] + [value for series in series_map.values() for value in series])

        def build_points(values):
            if len(values) == 1:
                x = padding_left + chart_width / 2
                y = padding_top + chart_height - ((values[0] / max_value) * chart_height)
                return f"{x:.2f},{y:.2f}"
            points = []
            for index, value in enumerate(values):
                x = padding_left + (chart_width * index / max(1, len(values) - 1))
                y = padding_top + chart_height - ((value / max_value) * chart_height)
                points.append(f"{x:.2f},{y:.2f}")
            return " ".join(points)

        grid_lines = []
        for index in range(5):
            y = padding_top + chart_height * index / 4
            grid_lines.append(
                f'<line x1="{padding_left}" y1="{y:.2f}" x2="{width - padding_right}" y2="{y:.2f}" class="o_grid_line" />'
            )

        label_nodes = []
        for index, label in enumerate(labels):
            if len(labels) == 1:
                x = padding_left + chart_width / 2
            else:
                x = padding_left + (chart_width * index / max(1, len(labels) - 1))
            label_nodes.append(
                f'<text x="{x:.2f}" y="{height - 14}" class="o_axis_label" text-anchor="middle">{html.escape(label)}</text>'
            )

        lines = []
        palette = {
            "Omzet": "o_line_omzet",
            "Cash Out": "o_line_cashout",
        }
        for name, values in series_map.items():
            points = build_points(values)
            lines.append(f'<polyline points="{points}" class="{palette[name]}" />')
            for point in points.split():
                x, y = point.split(",")
                lines.append(f'<circle cx="{x}" cy="{y}" r="3" class="{palette[name]} o_point" />')

        return f"""
            <svg viewBox="0 0 {width} {height}" class="o_brownie_chart_svg" role="img" aria-label="Revenue and cash out trend">
                <g>{''.join(grid_lines)}</g>
                <g>{''.join(lines)}</g>
                <g>{''.join(label_nodes)}</g>
            </svg>
        """

    def _build_vendor_bills_html(self, bills):
        rows = []
        for bill in bills[:10]:
            is_overdue = bool(bill.invoice_date_due and bill.invoice_date_due < fields.Date.context_today(self))
            status = _("Overdue") if is_overdue else _("Open")
            status_class = "overdue" if is_overdue else "open"
            bill_url = self._build_bill_form_url(bill)
            bill_link = self._build_bill_link_html(bill_url, bill.name or bill.ref or "-")
            rows.append(
                f"""
                <tr>
                    <td>{html.escape(bill.partner_id.display_name or '-')}</td>
                    <td>{bill_link}</td>
                    <td>{html.escape(format_date(self.env, bill.invoice_date_due) if bill.invoice_date_due else '-')}</td>
                    <td class="is-amount">{html.escape(self._format_idr(abs(bill.amount_residual)))}</td>
                    <td><span class="o_status {status_class}">{html.escape(status)}</span></td>
                </tr>
                """
            )
        if not rows:
            rows.append(
                """
                <tr>
                    <td colspan="5" class="is-empty">No vendor bills found in the selected period.</td>
                </tr>
                """
            )
        return f"""
            <div class="o_brownie_table_card">
                <div class="o_brownie_section_head">
                    <div>
                        <h3>Vendor Bills Belum Dibayar</h3>
                        <span>Only bills with remaining residual, sorted by nearest due date</span>
                    </div>
                </div>
                <table class="o_brownie_table">
                    <thead>
                        <tr>
                            <th>Vendor</th>
                            <th>Bill Number</th>
                            <th>Due Date</th>
                            <th>Amount</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        """

    def _build_unreconciled_bills_html(self, bills):
        rows = []
        for bill in bills[:10]:
            bill_url = self._build_bill_form_url(bill)
            bill_link = self._build_bill_link_html(bill_url, bill.name or bill.ref or "-")
            rows.append(
                f"""
                <tr>
                    <td>{html.escape(bill.partner_id.display_name or '-')}</td>
                    <td>{bill_link}</td>
                    <td>{html.escape(format_date(self.env, bill.invoice_date_due) if bill.invoice_date_due else '-')}</td>
                    <td class="is-amount">{html.escape(self._format_idr(abs(bill.amount_total)))}</td>
                    <td><span class="o_status in_payment">{html.escape(_('Belum Rekonsiliasi'))}</span></td>
                </tr>
                """
            )
        if not rows:
            rows.append(
                """
                <tr>
                    <td colspan="5" class="is-empty">No vendor bills awaiting reconciliation at the cutoff date.</td>
                </tr>
                """
            )
        return f"""
            <div class="o_brownie_table_card">
                <div class="o_brownie_section_head">
                    <div>
                        <h3>Vendor Bills Belum Direkonsiliasi</h3>
                        <span>Bills already in payment but not fully reconciled yet</span>
                    </div>
                </div>
                <table class="o_brownie_table">
                    <thead>
                        <tr>
                            <th>Vendor</th>
                            <th>Bill Number</th>
                            <th>Due Date</th>
                            <th>Amount</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        """

    def _build_filter_summary_html(self, date_start, date_end, due_bills, due_amount):
        previous_start, previous_end = self._get_previous_range(date_start, date_end)
        current_cash_out = self._get_cash_out_amount(date_start, date_end)
        previous_cash_out = self._get_cash_out_amount(previous_start, previous_end)
        spike_ratio = ((current_cash_out - previous_cash_out) / previous_cash_out * 100.0) if previous_cash_out else 0.0
        overdue_count = len(due_bills.filtered(lambda bill: bill.invoice_date_due and bill.invoice_date_due < fields.Date.context_today(self)))
        warning_text = (
            f"Cash out is {spike_ratio:.1f}% higher than the previous comparable period."
            if previous_cash_out and spike_ratio > 15
            else "Cash out is within the normal period variance."
        )
        return f"""
            <div class="o_brownie_summary_card">
                <div class="o_brownie_section_head">
                    <div>
                        <h3>Filter Summary &amp; Alerts</h3>
                        <span>{html.escape(self.filter_note or '')}</span>
                    </div>
                </div>
                <div class="o_summary_grid">
                    <div><span>Selected Mode</span><strong>{html.escape(dict(self._fields['filter_mode'].selection).get(self.filter_mode, 'Custom Range'))}</strong></div>
                    <div><span>Effective Range</span><strong>{html.escape(self._describe_range(date_start, date_end))}</strong></div>
                    <div><span>Data Cutoff</span><strong>{html.escape(format_date(self.env, date_end))}</strong></div>
                    <div><span>Overdue Bills</span><strong>{overdue_count}</strong></div>
                </div>
                <div class="o_summary_alerts">
                    <div class="o_alert_row">
                        <span class="o_alert_icon is-danger">!</span>
                        <div>
                            <strong>{overdue_count} overdue bills</strong>
                            <p>Total due snapshot in this period: {html.escape(self._format_idr(due_amount))}</p>
                        </div>
                    </div>
                    <div class="o_alert_row">
                        <span class="o_alert_icon is-warn">i</span>
                        <div>
                            <strong>Cash out check</strong>
                            <p>{html.escape(warning_text)}</p>
                        </div>
                    </div>
                </div>
            </div>
        """

    def _build_bank_card_html(self, journal, balance, date_start, cutoff_date):
        journal_name = journal.display_name if journal else _("Journal not found")
        account_number = journal.bank_acc_number if journal and journal.bank_acc_number else "-"
        stats = self._get_bank_period_stats(journal, date_start, cutoff_date, balance)
        trend_class = "is-up" if stats["net_change"] >= 0 else "is-down"
        trend_label = _("Naik") if stats["net_change"] >= 0 else _("Turun")
        return f"""
            <div class="o_brownie_bank_card">
                <div class="o_brownie_bank_head">
                    <div>
                        <h3>{html.escape(journal_name)}</h3>
                        <span>{html.escape(account_number)}</span>
                    </div>
                    <div class="o_brownie_bank_balance">
                        <span>Balance as of {html.escape(format_date(self.env, cutoff_date))}</span>
                        <strong>{html.escape(self._format_idr(balance))}</strong>
                    </div>
                </div>
                <div class="o_brownie_bank_period">
                    <span>Periode {html.escape(self._describe_range(date_start, cutoff_date))}</span>
                    <strong class="{trend_class}">{html.escape(trend_label)} {html.escape(self._format_idr(abs(stats["net_change"])))}</strong>
                </div>
                <div class="o_brownie_bank_metrics">
                    <div>
                        <span>Saldo Awal</span>
                        <strong>{html.escape(self._format_idr(stats["opening_balance"]))}</strong>
                    </div>
                    <div>
                        <span>Saldo Akhir</span>
                        <strong>{html.escape(self._format_idr(balance))}</strong>
                    </div>
                    <div>
                        <span>Uang Masuk</span>
                        <strong class="is-up">{html.escape(self._format_idr(stats["inflow"]))}</strong>
                    </div>
                    <div>
                        <span>Uang Keluar</span>
                        <strong class="is-down">{html.escape(self._format_idr(stats["outflow"]))}</strong>
                    </div>
                </div>
                <div class="o_brownie_bank_footer">
                    <span>{stats["transaction_count"]} transaksi posted di periode ini</span>
                    <span>Perubahan bersih: {html.escape(self._format_idr(stats["net_change"]))}</span>
                </div>
            </div>
        """

    def _get_bank_period_stats(self, journal, date_start, cutoff_date, ending_balance):
        if not journal or not journal.default_account_id:
            return {
                "opening_balance": 0.0,
                "inflow": 0.0,
                "outflow": 0.0,
                "net_change": 0.0,
                "transaction_count": 0,
            }
        opening_balance = self._get_journal_balance(journal, date_start - timedelta(days=1)) if date_start else 0.0
        aml_lines = self.env["account.move.line"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("parent_state", "=", "posted"),
                ("account_id", "=", journal.default_account_id.id),
                ("date", ">=", date_start),
                ("date", "<=", cutoff_date),
            ],
            order="date asc, id asc",
        )
        inflow = sum(line.balance for line in aml_lines if line.balance > 0)
        outflow = abs(sum(line.balance for line in aml_lines if line.balance < 0))
        net_change = ending_balance - opening_balance
        return {
            "opening_balance": opening_balance,
            "inflow": inflow,
            "outflow": outflow,
            "net_change": net_change,
            "transaction_count": len(aml_lines),
        }

    def _get_previous_range(self, date_start, date_end):
        span = (date_end - date_start).days + 1
        previous_end = date_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=span - 1)
        return previous_start, previous_end

    def _describe_range(self, date_start, date_end):
        if date_start == date_end:
            return format_date(self.env, date_start)
        return f"{format_date(self.env, date_start)} - {format_date(self.env, date_end)}"

    def _format_idr(self, amount):
        rounded = f"{amount:,.0f}".replace(",", ".")
        return f"Rp {rounded}"

    def _build_bill_form_url(self, bill):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        return f"{base_url}/web#id={bill.id}&model=account.move&view_type=form"

    def _build_bill_link_html(self, bill_url, label):
        safe_url = html.escape(bill_url, quote=True)
        safe_label = html.escape(label)
        return (
            f'<a href="{safe_url}" '
            f'target="_self" '
            f'style="color:#0f766e;font-weight:700;text-decoration:underline;cursor:pointer;">'
            f"{safe_label}"
            f"</a>"
        )

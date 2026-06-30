from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DailyFreeProductConfig(models.Model):
    _name = "daily.free.product.config"
    _description = "Daily Free Product Configuration"
    _order = "date_start desc, date desc, id desc"

    date_mode = fields.Selection(
        [("single_date", "Single Date"), ("date_range", "Date Range")],
        required=True,
        default="single_date",
    )
    date = fields.Date(
        index=True,
        default=fields.Date.context_today,
        help="Used for single-date rewards and preserved for legacy compatibility.",
    )
    date_start = fields.Date(index=True)
    date_end = fields.Date(index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    product_id = fields.Many2one(
        "product.product",
        domain=[("available_in_pos", "=", True)],
    )
    reward_product_ids = fields.Many2many(
        "product.product",
        "daily_free_product_config_product_rel",
        "config_id",
        "product_id",
        string="Reward Products",
        domain=[("available_in_pos", "=", True)],
    )
    reward_product_names = fields.Char(
        compute="_compute_reward_product_names",
        string="Reward Products",
    )
    product_tmpl_id = fields.Many2one(
        "product.template",
        related="product_id.product_tmpl_id",
        store=True,
    )
    active = fields.Boolean(default=True)

    def init(self):
        self.env.cr.execute(
            """
            INSERT INTO daily_free_product_config_product_rel (config_id, product_id)
            SELECT cfg.id, cfg.product_id
            FROM daily_free_product_config cfg
            WHERE cfg.product_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM daily_free_product_config_product_rel rel
                  WHERE rel.config_id = cfg.id
                    AND rel.product_id = cfg.product_id
              )
            """
        )

    @api.depends("reward_product_ids", "product_id")
    def _compute_reward_product_names(self):
        for record in self:
            record.reward_product_names = ", ".join(record.get_reward_products().mapped("display_name"))

    @api.onchange("date_mode", "date", "date_start", "date_end")
    def _onchange_reward_dates(self):
        for record in self:
            if record.date_mode == "single_date":
                single_date = record.date or record.date_start or record.date_end or fields.Date.context_today(record)
                record.date = single_date
                record.date_start = single_date
                record.date_end = single_date
            elif record.date_mode == "date_range":
                if not record.date_start and record.date:
                    record.date_start = record.date
                if not record.date_end and record.date_start:
                    record.date_end = record.date_start

    @api.onchange("reward_product_ids")
    def _onchange_reward_product_ids(self):
        for record in self:
            if record.reward_product_ids:
                record.product_id = record.reward_product_ids[:1]

    def _get_effective_date_range(self):
        self.ensure_one()
        if self.date_mode == "date_range":
            return self.date_start, self.date_end
        single_date = self.date or self.date_start or self.date_end
        return single_date, single_date

    def get_reward_products(self):
        self.ensure_one()
        return self.reward_product_ids or self.product_id

    def _is_effective_on(self, target_date):
        self.ensure_one()
        date_start, date_end = self._get_effective_date_range()
        return bool(date_start and date_end and date_start <= target_date <= date_end)

    @api.model
    def _company_active_reward_domain(self, company_id):
        return [
            ("company_id", "=", company_id),
            ("active", "=", True),
        ]

    @api.model
    def get_active_rewards_for_day(self, company_id, target_date):
        rewards = self.search(
            self._company_active_reward_domain(company_id),
            order="date_start asc, date asc, id asc",
        )
        return rewards.filtered(lambda reward: reward._is_effective_on(target_date))

    @api.model
    def get_active_reward_for_day(self, company_id, target_date):
        return self.get_active_rewards_for_day(company_id, target_date)[:1]

    @api.model
    def _extract_first_reward_product_id(self, reward_product_commands):
        if not reward_product_commands:
            return False
        reward_ids = []
        for command in reward_product_commands:
            if not isinstance(command, (list, tuple)) or not command:
                continue
            operation = command[0]
            if operation == 6 and len(command) > 2:
                reward_ids.extend(command[2] or [])
            elif operation == 4 and len(command) > 1:
                reward_ids.append(command[1])
            elif operation == 0 and len(command) > 2 and isinstance(command[2], dict):
                # Inline-created products are not supported for this field in practice, so ignore.
                continue
        return reward_ids[0] if reward_ids else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("product_id") and vals.get("reward_product_ids"):
                primary_product_id = self._extract_first_reward_product_id(vals["reward_product_ids"])
                if primary_product_id:
                    vals["product_id"] = primary_product_id
        records = super().create(vals_list)
        records._sync_primary_reward_product()
        return records

    def write(self, vals):
        if not vals.get("product_id") and vals.get("reward_product_ids"):
            primary_product_id = self._extract_first_reward_product_id(vals["reward_product_ids"])
            if primary_product_id:
                vals["product_id"] = primary_product_id
        result = super().write(vals)
        if "reward_product_ids" in vals:
            self._sync_primary_reward_product()
        return result

    def _sync_primary_reward_product(self):
        for record in self:
            if record.reward_product_ids:
                primary_product = record.reward_product_ids[:1]
                if record.product_id != primary_product:
                    super(DailyFreeProductConfig, record).write({"product_id": primary_product.id})

    @api.constrains("date_mode", "date", "date_start", "date_end")
    def _check_date_configuration(self):
        for record in self.filtered("active"):
            if record.date_mode == "date_range":
                if not record.date_start or not record.date_end:
                    raise ValidationError(_("Date start and date end are required for date-range rewards."))
                if record.date_end < record.date_start:
                    raise ValidationError(_("Date end must be greater than or equal to date start."))
            elif not record.date:
                raise ValidationError(_("Date is required for single-date rewards."))
            if not record.get_reward_products():
                raise ValidationError(_("At least one reward product must be configured."))

    @api.constrains("date_mode", "date", "date_start", "date_end", "company_id", "active")
    def _check_unique_active_reward(self):
        for record in self.filtered("active"):
            record_start, record_end = record._get_effective_date_range()
            if not record_start or not record_end:
                continue
            candidates = self.search(
                [
                    ("id", "!=", record.id),
                    ("company_id", "=", record.company_id.id),
                    ("active", "=", True),
                ]
            )
            for candidate in candidates:
                candidate_start, candidate_end = candidate._get_effective_date_range()
                if not candidate_start or not candidate_end:
                    continue
                if record_start <= candidate_end and candidate_start <= record_end:
                    raise ValidationError(
                        _(
                            "Active daily reward periods cannot overlap within the same company."
                        )
                    )

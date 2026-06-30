from odoo import api, fields, models
from odoo.exceptions import ValidationError


class PosConfig(models.Model):
    _inherit = "pos.config"

    simulation_opening_hour = fields.Float(
        string="Simulation Opening Hour",
        default=8.0,
        help="Default local opening hour used by POS sales simulation batches.",
    )
    simulation_closing_hour = fields.Float(
        string="Simulation Closing Hour",
        default=22.0,
        help="Default local closing hour used by POS sales simulation batches.",
    )
    simulation_customer_mode = fields.Selection(
        [("auto_contact", "Auto Contact Pool")],
        string="Simulation Customer Source",
        default="auto_contact",
        required=True,
        help="Default customer source used by POS sales simulation batches.",
    )
    simulation_pos_category_ids = fields.Many2many(
        "pos.category",
        "pos_config_simulation_pos_category_rel",
        "config_id",
        "category_id",
        string="Simulation POS Categories",
        help="POS categories used as the default product source for simulation batches.",
    )
    simulation_product_rule_ids = fields.One2many(
        "pos.sales.simulation.product.rule",
        "config_id",
        string="Simulation Product Rules",
    )
    simulation_payment_rule_ids = fields.One2many(
        "pos.sales.simulation.payment.rule",
        "config_id",
        string="Simulation Payment Rules",
    )
    simulation_min_transaction_amount = fields.Monetary(
        string="Simulation Minimum Ticket",
        currency_field="currency_id",
        default=50.0,
        help="Default minimum ticket amount used by POS sales simulation batches.",
    )
    simulation_max_transaction_amount = fields.Monetary(
        string="Simulation Maximum Ticket",
        currency_field="currency_id",
        default=500.0,
        help="Default maximum ticket amount used by POS sales simulation batches.",
    )
    simulation_target_tolerance_pct = fields.Float(
        string="Simulation Target Tolerance (%)",
        default=5.0,
        help="Allowed deviation from the nominal target revenue for each simulation batch.",
    )
    simulation_min_lines_per_order = fields.Integer(
        string="Simulation Minimum Basket Lines",
        default=2,
        help="Minimum number of basket lines generated per simulated transaction.",
    )
    simulation_max_lines_per_order = fields.Integer(
        string="Simulation Maximum Basket Lines",
        default=4,
        help="Maximum number of basket lines generated per simulated transaction.",
    )
    simulation_peak_start_hour = fields.Float(
        string="Simulation Peak Start Hour",
        default=11.0,
        help="Start of the preferred peak-hour window used by POS sales simulation batches.",
    )
    simulation_peak_end_hour = fields.Float(
        string="Simulation Peak End Hour",
        default=14.0,
        help="End of the preferred peak-hour window used by POS sales simulation batches.",
    )
    simulation_peak_ratio = fields.Float(
        string="Simulation Peak Ratio",
        default=0.6,
        help="Share of simulated transactions that should fall inside the peak-hour window.",
    )

    @api.constrains(
        "simulation_opening_hour",
        "simulation_closing_hour",
        "simulation_peak_start_hour",
        "simulation_peak_end_hour",
        "simulation_peak_ratio",
        "simulation_min_transaction_amount",
        "simulation_max_transaction_amount",
        "simulation_target_tolerance_pct",
        "simulation_min_lines_per_order",
        "simulation_max_lines_per_order",
    )
    def _check_simulation_settings(self):
        for config in self:
            if not 0.0 <= config.simulation_opening_hour < 24.0:
                raise ValidationError("Simulation opening hour must be between 00:00 and 24:00.")
            if not 0.0 < config.simulation_closing_hour <= 24.0:
                raise ValidationError("Simulation closing hour must be between 00:00 and 24:00.")
            if config.simulation_opening_hour >= config.simulation_closing_hour:
                raise ValidationError("Simulation opening hour must be earlier than closing hour.")
            if not 0.0 <= config.simulation_peak_start_hour < 24.0:
                raise ValidationError("Simulation peak start hour must be between 00:00 and 24:00.")
            if not 0.0 < config.simulation_peak_end_hour <= 24.0:
                raise ValidationError("Simulation peak end hour must be between 00:00 and 24:00.")
            if config.simulation_peak_start_hour >= config.simulation_peak_end_hour:
                raise ValidationError("Simulation peak start hour must be earlier than peak end hour.")
            if not 0.0 <= config.simulation_peak_ratio <= 1.0:
                raise ValidationError("Simulation peak ratio must be between 0 and 1.")
            if config.simulation_min_transaction_amount <= 0 or config.simulation_max_transaction_amount <= 0:
                raise ValidationError("Simulation ticket amounts must be greater than zero.")
            if config.simulation_min_transaction_amount > config.simulation_max_transaction_amount:
                raise ValidationError("Simulation minimum ticket amount must not exceed the maximum.")
            if config.simulation_target_tolerance_pct < 0 or config.simulation_target_tolerance_pct > 100:
                raise ValidationError("Simulation target tolerance must be between 0 and 100 percent.")
            if config.simulation_min_lines_per_order <= 0 or config.simulation_max_lines_per_order <= 0:
                raise ValidationError("Simulation basket line counts must be greater than zero.")
            if config.simulation_min_lines_per_order > config.simulation_max_lines_per_order:
                raise ValidationError("Simulation minimum basket lines must not exceed the maximum.")


class PosSalesSimulationProductRule(models.Model):
    _name = "pos.sales.simulation.product.rule"
    _description = "POS Sales Simulation Product Rule"
    _order = "config_id, sequence, id"
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="config_id.company_id",
        store=True,
        readonly=True,
    )
    pos_category_id = fields.Many2one(
        "pos.category",
        string="POS Category",
        required=True,
    )
    product_id = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        domain=[("sale_ok", "=", True), ("product_tmpl_id.available_in_pos", "=", True)],
    )
    weight = fields.Float(default=1.0, required=True)
    min_qty = fields.Integer(string="Minimum Qty", default=1, required=True)
    max_qty = fields.Integer(string="Maximum Qty", default=3, required=True)

    @api.constrains("weight", "min_qty", "max_qty", "pos_category_id", "product_id", "config_id")
    def _check_rule_values(self):
        for rule in self:
            if rule.weight <= 0:
                raise ValidationError("Simulation product rule weight must be greater than zero.")
            if rule.min_qty <= 0 or rule.max_qty <= 0:
                raise ValidationError("Simulation product rule quantities must be greater than zero.")
            if rule.min_qty > rule.max_qty:
                raise ValidationError("Simulation product rule minimum quantity must not exceed the maximum.")
            if rule.config_id.simulation_pos_category_ids and rule.pos_category_id not in rule.config_id.simulation_pos_category_ids:
                raise ValidationError("Simulation product rule category must belong to the POS template categories.")
            if rule.pos_category_id not in rule.product_id.product_tmpl_id.pos_categ_ids:
                raise ValidationError("Simulation product rule product must belong to the selected POS category.")


class PosSalesSimulationPaymentRule(models.Model):
    _name = "pos.sales.simulation.payment.rule"
    _description = "POS Sales Simulation Payment Rule"
    _order = "config_id, sequence, id"
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        ondelete="cascade",
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="config_id.company_id",
        store=True,
        readonly=True,
    )
    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Payment Method",
        required=True,
        check_company=True,
    )
    weight = fields.Float(default=1.0, required=True)

    @api.constrains("weight", "payment_method_id", "config_id")
    def _check_payment_rule_values(self):
        for rule in self:
            if rule.weight <= 0:
                raise ValidationError("Simulation payment rule weight must be greater than zero.")
            if rule.payment_method_id not in rule.config_id.payment_method_ids:
                raise ValidationError("Simulation payment rule method must belong to the POS payment methods.")

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

    @api.constrains("simulation_opening_hour", "simulation_closing_hour")
    def _check_simulation_hours(self):
        for config in self:
            if not 0.0 <= config.simulation_opening_hour < 24.0:
                raise ValidationError("Simulation opening hour must be between 00:00 and 24:00.")
            if not 0.0 < config.simulation_closing_hour <= 24.0:
                raise ValidationError("Simulation closing hour must be between 00:00 and 24:00.")
            if config.simulation_opening_hour >= config.simulation_closing_hour:
                raise ValidationError("Simulation opening hour must be earlier than closing hour.")

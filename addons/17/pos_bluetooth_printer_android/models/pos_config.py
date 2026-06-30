from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    bluetooth_printer_enabled = fields.Boolean(
        string="Bluetooth Receipt Printer",
        help="Allow POS running in Android Chrome to print directly to a paired Bluetooth thermal printer.",
    )
    bluetooth_printer_auto_print = fields.Boolean(
        string="Auto Print Receipt",
        help="Automatically print the receipt after payment when the Bluetooth printer is already authorized on this tablet.",
    )
    bluetooth_printer_paper_width = fields.Selection(
        [
            ("58", "58 mm"),
            ("80", "80 mm"),
        ],
        string="Paper Width",
        default="58",
        required=True,
    )
    bluetooth_printer_baud_rate = fields.Selection(
        [
            ("9600", "9600"),
            ("19200", "19200"),
            ("38400", "38400"),
            ("57600", "57600"),
            ("115200", "115200"),
        ],
        string="Baud Rate",
        default="9600",
        required=True,
        help="Serial speed used by the Bluetooth printer profile.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    bluetooth_printer_enabled = fields.Boolean(
        related="pos_config_id.bluetooth_printer_enabled",
        readonly=False,
    )
    bluetooth_printer_auto_print = fields.Boolean(
        related="pos_config_id.bluetooth_printer_auto_print",
        readonly=False,
    )
    bluetooth_printer_paper_width = fields.Selection(
        related="pos_config_id.bluetooth_printer_paper_width",
        readonly=False,
    )
    bluetooth_printer_baud_rate = fields.Selection(
        related="pos_config_id.bluetooth_printer_baud_rate",
        readonly=False,
    )


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        fields_to_load = result["search_params"].get("fields")
        if fields_to_load:
            for field_name in [
                "bluetooth_printer_enabled",
                "bluetooth_printer_auto_print",
                "bluetooth_printer_paper_width",
                "bluetooth_printer_baud_rate",
            ]:
                if field_name not in fields_to_load:
                    fields_to_load.append(field_name)
        return result

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    brownielab_payment_reminder_enabled = fields.Boolean(
        string="Show Payment Reminder Popup",
        help="Display a cashier reminder popup after validating a paid POS order.",
    )
    brownielab_payment_reminder_message = fields.Text(
        string="Payment Reminder Message",
        default="• Sudah upselling?\n• Jangan lupa senyum dan ucapkan terimakasih",
        help="Message shown to the cashier after clicking Validate on the payment screen.",
    )
    brownielab_payment_reminder_preset = fields.Selection(
        [
            ("custom", "Custom"),
            ("cashier_far_read", "Kasir Jauh Baca"),
            ("minimal_clean", "Minimal Clean"),
        ],
        string="Payment Reminder Preset",
        default="custom",
        help="Template preset for the payment reminder popup. After choosing a preset, each field can still be edited manually.",
    )
    brownielab_payment_reminder_font_size = fields.Integer(
        string="Payment Reminder Font Size",
        default=30,
        help="Base font size in pixels for the reminder popup text shown in POS.",
    )
    brownielab_payment_reminder_title_font_size = fields.Integer(
        string="Payment Reminder Title Font Size",
        default=38,
    )
    brownielab_payment_reminder_button_font_size = fields.Integer(
        string="Payment Reminder Button Font Size",
        default=28,
    )
    brownielab_payment_reminder_font_family = fields.Char(
        string="Payment Reminder Font Family",
        default="inherit",
        help="CSS font-family value used by the popup, for example Inter, Arial, or inherit.",
    )
    brownielab_payment_reminder_title_bold = fields.Boolean(
        string="Payment Reminder Title Bold",
        default=True,
    )
    brownielab_payment_reminder_body_bold = fields.Boolean(
        string="Payment Reminder Body Bold",
        default=True,
    )
    brownielab_payment_reminder_button_bold = fields.Boolean(
        string="Payment Reminder Button Bold",
        default=True,
    )
    brownielab_payment_reminder_title_italic = fields.Boolean(
        string="Payment Reminder Title Italic",
    )
    brownielab_payment_reminder_body_italic = fields.Boolean(
        string="Payment Reminder Body Italic",
    )
    brownielab_payment_reminder_button_italic = fields.Boolean(
        string="Payment Reminder Button Italic",
    )
    brownielab_payment_reminder_title_underline = fields.Boolean(
        string="Payment Reminder Title Underline",
    )
    brownielab_payment_reminder_body_underline = fields.Boolean(
        string="Payment Reminder Body Underline",
    )
    brownielab_payment_reminder_button_underline = fields.Boolean(
        string="Payment Reminder Button Underline",
    )
    brownielab_payment_reminder_title_align = fields.Selection(
        [
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        string="Payment Reminder Title Alignment",
        default="center",
    )
    brownielab_payment_reminder_body_align = fields.Selection(
        [
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        string="Payment Reminder Body Alignment",
        default="left",
    )
    brownielab_payment_reminder_text_color = fields.Char(
        string="Payment Reminder Text Color",
        default="#1f2937",
        help="CSS color value for the title and body text.",
    )
    brownielab_payment_reminder_button_background = fields.Char(
        string="Payment Reminder Button Background",
        default="#7a4d72",
        help="CSS color value for the OK button background.",
    )
    brownielab_payment_reminder_button_text_color = fields.Char(
        string="Payment Reminder Button Text Color",
        default="#ffffff",
        help="CSS color value for the OK button text.",
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    _BROWNIELAB_PAYMENT_REMINDER_PRESETS = {
        "cashier_far_read": {
            "brownielab_payment_reminder_font_size": 38,
            "brownielab_payment_reminder_title_font_size": 52,
            "brownielab_payment_reminder_button_font_size": 34,
            "brownielab_payment_reminder_font_family": "Arial, Helvetica, sans-serif",
            "brownielab_payment_reminder_title_bold": True,
            "brownielab_payment_reminder_body_bold": True,
            "brownielab_payment_reminder_button_bold": True,
            "brownielab_payment_reminder_title_italic": False,
            "brownielab_payment_reminder_body_italic": False,
            "brownielab_payment_reminder_button_italic": False,
            "brownielab_payment_reminder_title_underline": False,
            "brownielab_payment_reminder_body_underline": False,
            "brownielab_payment_reminder_button_underline": False,
            "brownielab_payment_reminder_title_align": "center",
            "brownielab_payment_reminder_body_align": "left",
            "brownielab_payment_reminder_text_color": "#111827",
            "brownielab_payment_reminder_button_background": "#7a4d72",
            "brownielab_payment_reminder_button_text_color": "#ffffff",
        },
        "minimal_clean": {
            "brownielab_payment_reminder_font_size": 26,
            "brownielab_payment_reminder_title_font_size": 34,
            "brownielab_payment_reminder_button_font_size": 24,
            "brownielab_payment_reminder_font_family": "inherit",
            "brownielab_payment_reminder_title_bold": True,
            "brownielab_payment_reminder_body_bold": False,
            "brownielab_payment_reminder_button_bold": True,
            "brownielab_payment_reminder_title_italic": False,
            "brownielab_payment_reminder_body_italic": False,
            "brownielab_payment_reminder_button_italic": False,
            "brownielab_payment_reminder_title_underline": False,
            "brownielab_payment_reminder_body_underline": False,
            "brownielab_payment_reminder_button_underline": False,
            "brownielab_payment_reminder_title_align": "center",
            "brownielab_payment_reminder_body_align": "center",
            "brownielab_payment_reminder_text_color": "#1f2937",
            "brownielab_payment_reminder_button_background": "#7a4d72",
            "brownielab_payment_reminder_button_text_color": "#ffffff",
        },
    }

    brownielab_payment_reminder_enabled = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_enabled",
        readonly=False,
    )
    brownielab_payment_reminder_message = fields.Text(
        related="pos_config_id.brownielab_payment_reminder_message",
        readonly=False,
    )
    brownielab_payment_reminder_preset = fields.Selection(
        related="pos_config_id.brownielab_payment_reminder_preset",
        readonly=False,
    )
    brownielab_payment_reminder_font_size = fields.Integer(
        related="pos_config_id.brownielab_payment_reminder_font_size",
        readonly=False,
    )
    brownielab_payment_reminder_title_font_size = fields.Integer(
        related="pos_config_id.brownielab_payment_reminder_title_font_size",
        readonly=False,
    )
    brownielab_payment_reminder_button_font_size = fields.Integer(
        related="pos_config_id.brownielab_payment_reminder_button_font_size",
        readonly=False,
    )
    brownielab_payment_reminder_font_family = fields.Char(
        related="pos_config_id.brownielab_payment_reminder_font_family",
        readonly=False,
    )
    brownielab_payment_reminder_title_bold = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_title_bold",
        readonly=False,
    )
    brownielab_payment_reminder_body_bold = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_body_bold",
        readonly=False,
    )
    brownielab_payment_reminder_button_bold = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_button_bold",
        readonly=False,
    )
    brownielab_payment_reminder_title_italic = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_title_italic",
        readonly=False,
    )
    brownielab_payment_reminder_body_italic = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_body_italic",
        readonly=False,
    )
    brownielab_payment_reminder_button_italic = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_button_italic",
        readonly=False,
    )
    brownielab_payment_reminder_title_underline = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_title_underline",
        readonly=False,
    )
    brownielab_payment_reminder_body_underline = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_body_underline",
        readonly=False,
    )
    brownielab_payment_reminder_button_underline = fields.Boolean(
        related="pos_config_id.brownielab_payment_reminder_button_underline",
        readonly=False,
    )
    brownielab_payment_reminder_title_align = fields.Selection(
        related="pos_config_id.brownielab_payment_reminder_title_align",
        readonly=False,
    )
    brownielab_payment_reminder_body_align = fields.Selection(
        related="pos_config_id.brownielab_payment_reminder_body_align",
        readonly=False,
    )
    brownielab_payment_reminder_text_color = fields.Char(
        related="pos_config_id.brownielab_payment_reminder_text_color",
        readonly=False,
    )
    brownielab_payment_reminder_button_background = fields.Char(
        related="pos_config_id.brownielab_payment_reminder_button_background",
        readonly=False,
    )
    brownielab_payment_reminder_button_text_color = fields.Char(
        related="pos_config_id.brownielab_payment_reminder_button_text_color",
        readonly=False,
    )

    @api.onchange("brownielab_payment_reminder_preset")
    def _onchange_brownielab_payment_reminder_preset(self):
        for setting in self:
            preset = setting.brownielab_payment_reminder_preset
            if not preset or preset == "custom":
                continue
            values = setting._BROWNIELAB_PAYMENT_REMINDER_PRESETS.get(preset, {})
            for field_name, value in values.items():
                setattr(setting, field_name, value)


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_pos_config(self):
        result = super()._loader_params_pos_config()
        fields_to_load = result["search_params"].get("fields")
        if fields_to_load:
            for field_name in [
                "brownielab_payment_reminder_enabled",
                "brownielab_payment_reminder_message",
                "brownielab_payment_reminder_font_size",
                "brownielab_payment_reminder_title_font_size",
                "brownielab_payment_reminder_button_font_size",
                "brownielab_payment_reminder_font_family",
                "brownielab_payment_reminder_title_bold",
                "brownielab_payment_reminder_body_bold",
                "brownielab_payment_reminder_button_bold",
                "brownielab_payment_reminder_title_italic",
                "brownielab_payment_reminder_body_italic",
                "brownielab_payment_reminder_button_italic",
                "brownielab_payment_reminder_title_underline",
                "brownielab_payment_reminder_body_underline",
                "brownielab_payment_reminder_button_underline",
                "brownielab_payment_reminder_title_align",
                "brownielab_payment_reminder_body_align",
                "brownielab_payment_reminder_text_color",
                "brownielab_payment_reminder_button_background",
                "brownielab_payment_reminder_button_text_color",
            ]:
                if field_name not in fields_to_load:
                    fields_to_load.append(field_name)
        return result

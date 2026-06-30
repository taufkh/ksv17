from odoo import api, fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="Sales Channel",
        index=True,
        ondelete="set null",
    )
    online_check_qty = fields.Float(
        string="Checked Quantity",
        copy=False,
        default=0.0,
    )
    online_check_status = fields.Selection(
        [
            ("unchecked", "Unchecked"),
            ("partial", "Partial"),
            ("full", "Full"),
        ],
        string="Online Check Status",
        compute="_compute_online_check_status",
    )

    def _order_line_fields(self, line, session_id=None):
        result = super()._order_line_fields(line, session_id=session_id)
        data = line[2] if len(line) > 2 else {}
        if isinstance(result, (list, tuple)) and len(result) > 2 and isinstance(result[2], dict):
            result[2]["sale_channel_id"] = data.get("sale_channel_id") or False
            result[2]["online_check_qty"] = data.get("online_check_qty") or 0.0
            return result

        if isinstance(result, dict):
            result["sale_channel_id"] = data.get("sale_channel_id") or False
            result["online_check_qty"] = data.get("online_check_qty") or 0.0
        return result

    @api.depends("online_check_qty", "qty")
    def _compute_online_check_status(self):
        for line in self:
            ordered_qty = max(line.qty or 0.0, 0.0)
            checked_qty = min(max(line.online_check_qty or 0.0, 0.0), ordered_qty)
            if ordered_qty <= 0.0 or checked_qty <= 0.0:
                line.online_check_status = "unchecked"
            elif checked_qty >= ordered_qty:
                line.online_check_status = "full"
            else:
                line.online_check_status = "partial"

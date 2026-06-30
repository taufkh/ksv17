from odoo import fields, models


class PosOrderReport(models.Model):
    _inherit = "report.pos.order"

    sale_channel_id = fields.Many2one("pos.sale.channel", string="Sales Channel", readonly=True)

    def _select(self):
        return super()._select() + ", COALESCE(l.sale_channel_id, s.sale_channel_id) AS sale_channel_id"

    def _group_by(self):
        return super()._group_by() + ", COALESCE(l.sale_channel_id, s.sale_channel_id)"

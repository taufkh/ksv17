from odoo import fields, models


class PosSaleChannelChangeLog(models.Model):
    _name = "pos.sale.channel.change.log"
    _description = "POS Sale Channel Change Log"
    _order = "change_datetime desc, id desc"

    order_id = fields.Many2one(
        "pos.order",
        string="POS Order",
        required=True,
        index=True,
        ondelete="cascade",
    )
    session_id = fields.Many2one(
        related="order_id.session_id",
        store=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        related="order_id.company_id",
        store=True,
        readonly=True,
    )
    old_sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="Old Sales Channel",
        readonly=True,
    )
    new_sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        string="New Sales Channel",
        required=True,
        readonly=True,
    )
    change_datetime = fields.Datetime(
        string="Changed At",
        required=True,
        readonly=True,
        default=fields.Datetime.now,
    )
    executed_by_id = fields.Many2one(
        "res.users",
        string="Executed By",
        required=True,
        readonly=True,
    )
    used_pin_masked = fields.Char(
        string="Used PIN (Masked)",
        readonly=True,
    )

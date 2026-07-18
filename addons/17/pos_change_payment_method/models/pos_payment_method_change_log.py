from odoo import fields, models


class PosPaymentMethodChangeLog(models.Model):
    _name = "pos.payment.method.change.log"
    _description = "POS Payment Method Change Log"
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
    currency_id = fields.Many2one(
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )
    old_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Old Payment Method",
        required=True,
        readonly=True,
    )
    new_payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="New Payment Method",
        required=True,
        readonly=True,
    )
    payment_amount = fields.Monetary(
        string="Payment Amount",
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

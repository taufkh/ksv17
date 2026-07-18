from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class PosBackendSaleChannelRevisionWizard(models.TransientModel):
    _name = "pos.backend.sale.channel.revision.wizard"
    _description = "POS Backend Sale Channel Revision Wizard"

    order_id = fields.Many2one("pos.order", required=True, readonly=True)
    company_id = fields.Many2one(related="order_id.company_id", readonly=True)
    current_sale_channel_id = fields.Many2one("pos.sale.channel", readonly=True)
    new_sale_channel_id = fields.Many2one(
        "pos.sale.channel",
        required=True,
    )
    available_sale_channel_ids = fields.Many2many(
        "pos.sale.channel",
        compute="_compute_available_sale_channel_ids",
    )
    reason = fields.Text(required=True)

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        order = self.env["pos.order"].browse(self.env.context.get("active_id"))
        if not order.exists():
            return values

        order._check_backend_sale_channel_revision_allowed()
        values.update(
            {
                "order_id": order.id,
                "current_sale_channel_id": order.sale_channel_id.id,
            }
        )
        return values

    @api.depends("order_id")
    def _compute_available_sale_channel_ids(self):
        for wizard in self:
            channels = wizard.order_id._get_changeable_sale_channels()
            wizard.available_sale_channel_ids = [Command.set(channels.ids)]

    def _check_finance_access(self):
        if not self.env.user.has_group("bakery_user_roles.group_bakery_finance"):
            raise UserError(_("Only Finance can revise POS sales channel from the backend."))

    def action_apply_revision(self):
        self.ensure_one()
        self._check_finance_access()
        if not self.reason or not self.reason.strip():
            raise ValidationError(_("Revision reason is required."))
        allowed_channels = self.order_id._get_changeable_sale_channels()
        if self.new_sale_channel_id not in allowed_channels:
            raise ValidationError(
                _("Sales channel %(channel)s is not allowed for this POS order.")
                % {"channel": self.new_sale_channel_id.display_name}
            )

        self.order_id.action_backend_revise_sale_channel(self.new_sale_channel_id, self.reason)
        return {"type": "ir.actions.act_window_close"}

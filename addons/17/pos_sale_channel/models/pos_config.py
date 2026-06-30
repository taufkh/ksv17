from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    online_checker_channel_ids = fields.Many2many(
        "pos.sale.channel",
        "pos_config_online_checker_channel_rel",
        "config_id",
        "channel_id",
        string="Online Checker Channels",
        help="Orders using these channels will require the online item checker after payment.",
    )
    online_checker_can_manage = fields.Boolean(
        compute="_compute_online_checker_can_manage",
    )

    def _compute_online_checker_can_manage(self):
        can_manage = self.env.user.has_group("point_of_sale.group_pos_manager")
        for config in self:
            config.online_checker_can_manage = can_manage

    def get_online_checker_recap_url(self):
        self.ensure_one()
        action = self.env.ref("pos_sale_channel.action_pos_online_checker_recap_wizard")
        menu = self.env.ref("pos_sale_channel.menu_pos_online_checker_recap")
        return f"/web#action={action.id}&model=pos.online.checker.recap.wizard&view_type=form&menu_id={menu.id}"

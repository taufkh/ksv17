from datetime import datetime, time

from odoo import _, fields, models


class PosOnlineCheckerRecapWizard(models.TransientModel):
    _name = "pos.online.checker.recap.wizard"
    _description = "POS Online Checker Recap Wizard"

    date_from = fields.Date(
        string="Date From",
        default=fields.Date.context_today,
    )
    date_to = fields.Date(
        string="Date To",
        default=fields.Date.context_today,
    )
    config_ids = fields.Many2many(
        "pos.config",
        "pos_online_checker_recap_wizard_config_rel",
        "wizard_id",
        "config_id",
        string="Point of Sale",
    )
    sale_channel_ids = fields.Many2many(
        "pos.sale.channel",
        "pos_online_checker_recap_wizard_channel_rel",
        "wizard_id",
        "channel_id",
        string="Sales Channels",
    )
    online_check_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("checked", "Checked"),
            ("overridden", "Overridden"),
        ],
        string="Checker Status",
    )

    def _get_report_domain(self):
        self.ensure_one()
        domain = [("online_check_required", "=", True)]
        if self.date_from:
            domain.append(
                (
                    "date_order",
                    ">=",
                    fields.Datetime.to_string(datetime.combine(self.date_from, time.min)),
                )
            )
        if self.date_to:
            domain.append(
                (
                    "date_order",
                    "<=",
                    fields.Datetime.to_string(datetime.combine(self.date_to, time.max)),
                )
            )
        if self.config_ids:
            domain.append(("config_id", "in", self.config_ids.ids))
        if self.sale_channel_ids:
            domain.append(("sale_channel_id", "in", self.sale_channel_ids.ids))
        if self.online_check_status:
            domain.append(("online_check_status", "=", self.online_check_status))
        return domain

    def _get_report_orders(self):
        self.ensure_one()
        return self.env["pos.order"].search(self._get_report_domain(), order="date_order desc, id desc")

    def _get_status_label(self):
        self.ensure_one()
        if not self.online_check_status:
            return _("All")
        return dict(self._fields["online_check_status"].selection).get(self.online_check_status, self.online_check_status)

    def action_open_report(self):
        self.ensure_one()
        action = self.env.ref("pos_sale_channel.action_pos_online_checker_recap_orders").read()[0]
        action["domain"] = self._get_report_domain()
        action["context"] = {
            **self.env.context,
            "search_default_group_by_online_check_status": 0,
            "search_default_group_by_sale_channel": 0,
        }
        return action

    def action_export_xlsx(self):
        self.ensure_one()
        return {
            "name": _("Export Online Checker Recap XLSX"),
            "type": "ir.actions.act_url",
            "url": f"/pos_sale_channel/online_checker_recap/{self.id}/xlsx",
            "target": "self",
        }

from werkzeug.exceptions import Forbidden
from werkzeug.utils import redirect

from odoo import fields, http
from odoo.http import request


class PosMembershipPortalController(http.Controller):
    def _get_member_partner(self):
        partner = request.env.user.partner_id
        if not partner or not partner.is_custom_member:
            raise Forbidden()
        return partner.sudo()

    @http.route("/member/login", type="http", auth="public", website=True, sitemap=False)
    def member_login(self, **kwargs):
        if request.session.uid:
            return redirect("/member/dashboard")
        return request.render(
            "pos_membership.member_login",
            {
                "csrf_token": request.csrf_token(),
                "login": kwargs.get("login", ""),
                "redirect_url": "/member/dashboard",
            },
        )

    @http.route("/member/dashboard", type="http", auth="user", website=True, sitemap=False)
    def member_dashboard(self, **kwargs):
        partner = self._get_member_partner()
        today = fields.Date.context_today(partner)
        deposit_logs = request.env["membership.deposit.ledger"].sudo().search(
            [("partner_id", "=", partner.id)],
            order="date desc, id desc",
            limit=10,
        )
        point_logs = request.env["membership.point.ledger"].sudo().search(
            [("partner_id", "=", partner.id)],
            order="date desc, id desc",
            limit=10,
        )
        reward_config_model = request.env["daily.free.product.config"].sudo()
        reward_configs = reward_config_model.search(
            [
                ("company_id", "=", partner.company_id.id or request.env.company.id),
                ("active", "=", True),
            ],
            order="date_start asc, date asc, id asc",
        )
        reward_configs = reward_configs.filtered(
            lambda reward: (
                (reward.date_mode == "date_range" and reward.date_end and reward.date_end >= today)
                or (reward.date_mode == "single_date" and reward.date and reward.date >= today)
                or (not reward.date_mode and reward.date and reward.date >= today)
            )
        )[:10]
        return request.render(
            "pos_membership.member_dashboard",
            {
                "partner": partner,
                "deposit_logs": deposit_logs,
                "point_logs": point_logs,
                "reward_configs": reward_configs,
                "today": today,
            },
        )

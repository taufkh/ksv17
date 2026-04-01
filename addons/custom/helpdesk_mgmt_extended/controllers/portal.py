# -*- coding: utf-8 -*-
import werkzeug

from odoo import http, _
from odoo.http import request
from odoo.addons.helpdesk_mgmt.controllers.main import HelpdeskTicketController


class HelpdeskTicketControllerExtended(HelpdeskTicketController):
    """
    Extended portal controller consolidating:
      • helpdesk_type              — inject ticket types into the new-ticket form
      • helpdesk_portal_restriction — filter teams/categories by partner access
      • helpdesk_ticket_partner_response — customer reply endpoint
    """

    def _is_extended_feature_enabled(self):
        return request.env["helpdesk.feature.config"].sudo().is_enabled(
            "helpdesk.core.extended"
        )

    def _get_teams(self):
        """Override to filter teams by the portal restriction partner list."""
        if not self._is_extended_feature_enabled():
            return super()._get_teams()
        teams = super()._get_teams()
        partner = request.env.user.partner_id
        if teams and partner:
            teams = teams.filtered(
                lambda t: not t.helpdesk_partner_ids or partner in t.helpdesk_partner_ids
            )
        return teams

    @http.route("/new/ticket", type="http", auth="user", website=True)
    def create_new_ticket(self, **kw):
        """Override to add ticket types and category portal restriction."""
        if not self._is_extended_feature_enabled():
            return super().create_new_ticket(**kw)
        company = request.env.company
        partner = request.env.user.partner_id

        # Base categories filtered by portal restriction
        categories = request.env["helpdesk.ticket.category"].with_company(company.id).search(
            [("active", "=", True), ("show_in_portal", "=", True)]
        )
        if partner:
            categories = categories.filtered(
                lambda c: not c.helpdesk_category_partner_ids
                or partner in c.helpdesk_category_partner_ids
            )

        # Ticket types (only if company setting is enabled)
        show_type = company.helpdesk_mgmt_portal_type
        types = request.env["helpdesk.ticket.type"].sudo().search(
            [("show_in_portal", "=", True)]
        ) if show_type else request.env["helpdesk.ticket.type"]

        session_info = request.env["ir.http"].session_info()
        return request.render(
            "helpdesk_mgmt.portal_create_ticket",
            {
                "categories": categories,
                "teams": self._get_teams(),
                "types": types,
                "show_type": show_type,
                "email": request.env.user.email,
                "name": request.env.user.name,
                "ticket_team_id_required": company.helpdesk_mgmt_portal_team_id_required,
                "ticket_category_id_required": company.helpdesk_mgmt_portal_category_id_required,
                "max_upload_size": session_info["max_file_upload_size"],
            },
        )

    def _prepare_submit_ticket_vals(self, **kw):
        """Override to capture the type_id field from the form."""
        vals = super()._prepare_submit_ticket_vals(**kw)
        if not self._is_extended_feature_enabled():
            return vals
        if kw.get("type_id"):
            vals["type_id"] = int(kw.get("type_id"))
        return vals

    # ── Customer reply ────────────────────────────────────────────────────────

    @http.route(
        ["/helpdesk/ticket/<int:ticket_id>/reply"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def customer_reply(self, ticket_id, message=None, **kwargs):
        """Allow the customer to reply to a ticket from the portal."""
        if not self._is_extended_feature_enabled():
            return request.not_found()
        ticket = request.env["helpdesk.ticket"].sudo().browse(ticket_id)
        if not ticket.exists():
            return request.not_found()
        if message:
            ticket.message_post(
                body=message,
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                author_id=request.env.user.partner_id.id,
            )
        return werkzeug.utils.redirect("/my/ticket/%d" % ticket_id)

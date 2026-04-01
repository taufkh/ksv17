from odoo import _, http
from odoo.http import request

from odoo.addons.helpdesk_custom_portal.controllers.portal import HelpdeskCustomPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class HelpdeskKnowledgePortal(HelpdeskCustomPortal):
    def _get_portal_root_partner(self):
        partner = request.env.user.partner_id
        return partner.commercial_partner_id or partner

    def _get_visible_articles(self, partner=None, ticket=None, search=None):
        partner = partner or self._get_portal_root_partner()
        article_model = request.env["document.page"].sudo()
        domain = [
            ("type", "=", "content"),
            ("is_helpdesk_article", "=", True),
            ("portal_publication_state", "=", "published"),
            ("active", "=", True),
        ]
        articles = article_model.search(domain, order="portal_published_on desc, write_date desc, id desc")
        if search:
            term = search.lower()
            articles = articles.filtered(
                lambda article: term in (article.name or "").lower()
                or term in (article.portal_summary or "").lower()
                or term in (article.portal_keywords or "").lower()
                or term in (article.content or "").lower()
            )
        articles = articles.filtered(
            lambda article: article._is_visible_for_portal(
                partner=partner,
                contract=ticket.support_contract_id if ticket else False,
                team=ticket.team_id if ticket else False,
            )
        )
        return articles

    def _get_suggested_articles(self, ticket, limit=4):
        articles = self._get_visible_articles(partner=ticket.commercial_partner_id, ticket=ticket)
        scored = []
        for article in articles:
            score = article._get_ticket_relevance_score(ticket)
            if score:
                scored.append((score, article.portal_view_count, article))
        scored.sort(key=lambda item: (item[0], item[1], item[2].id), reverse=True)
        return request.env["document.page"].sudo().concat(*(row[2] for row in scored[:limit])) if scored else request.env["document.page"]

    def _prepare_portal_article_list_values(self, articles, page=1, search=None):
        step = 10
        pager = portal_pager(
            url="/my/helpdesk/knowledge",
            url_args={"search": search} if search else {},
            total=len(articles),
            page=page,
            step=step,
        )
        current_articles = articles[pager["offset"] : pager["offset"] + step]
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "helpdesk_knowledge",
                "articles": current_articles,
                "pager": pager,
                "search": search,
                "default_url": "/my/helpdesk/knowledge",
            }
        )
        return values

    def _render_article_page(self, article, values):
        article._register_portal_view()
        values.update(
            {
                "page_name": "helpdesk_knowledge",
                "article": article,
            }
        )
        return request.render("helpdesk_custom_knowledge_portal.portal_helpdesk_knowledge_article", values)

    @http.route(
        ["/my/helpdesk/knowledge", "/my/helpdesk/knowledge/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_helpdesk_knowledge(self, page=1, search=None, **kw):
        articles = self._get_visible_articles(search=search)
        values = self._prepare_portal_article_list_values(articles, page=page, search=search)
        return request.render("helpdesk_custom_knowledge_portal.portal_my_helpdesk_knowledge", values)

    @http.route(
        ["/my/helpdesk/knowledge/<int:article_id>"],
        type="http",
        auth="user",
        website=True,
    )
    def portal_my_helpdesk_knowledge_article(self, article_id, **kw):
        article = request.env["document.page"].sudo().browse(article_id)
        if not article.exists() or not article._is_visible_for_portal(partner=self._get_portal_root_partner()):
            return request.redirect("/my/helpdesk/knowledge")
        values = self._prepare_portal_layout_values()
        return self._render_article_page(article, values)

    @http.route(
        ["/my/helpdesk/knowledge/<int:article_id>/feedback"],
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def portal_my_helpdesk_knowledge_feedback(self, article_id, helpful=None, **kw):
        article = request.env["document.page"].sudo().browse(article_id)
        if article.exists() and article._is_visible_for_portal(partner=self._get_portal_root_partner()):
            article._register_portal_feedback(helpful == "yes")
        return request.redirect(f"/my/helpdesk/knowledge/{article_id}?feedback=1")

    @http.route(
        ["/helpdesk/track/<string:token>/knowledge/<int:article_id>"],
        type="http",
        auth="public",
        website=True,
    )
    def public_ticket_knowledge_article(self, token, article_id, **kw):
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        article = request.env["document.page"].sudo().browse(article_id)
        if not article.exists() or not article._is_visible_for_portal(
            partner=ticket.commercial_partner_id,
            contract=ticket.support_contract_id,
            team=ticket.team_id,
        ):
            return request.not_found()
        values = self._prepare_public_ticket_values(ticket, **kw)
        values.update(
            {
                "article": article,
                "page_name": "ticket_public_knowledge",
            }
        )
        article._register_portal_view()
        return request.render("helpdesk_custom_knowledge_portal.public_helpdesk_knowledge_article", values)

    @http.route(
        ["/helpdesk/track/<string:token>/knowledge/<int:article_id>/feedback"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_knowledge_feedback(self, token, article_id, helpful=None, **kw):
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        article = request.env["document.page"].sudo().browse(article_id)
        if article.exists() and article._is_visible_for_portal(
            partner=ticket.commercial_partner_id,
            contract=ticket.support_contract_id,
            team=ticket.team_id,
        ):
            article._register_portal_feedback(helpful == "yes")
        return self._redirect_public_ticket(ticket, article_feedback=1, article_id=article_id)

    @http.route(
        ["/helpdesk/track/<string:token>/knowledge/<int:article_id>/deflect"],
        type="http",
        auth="public",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def public_ticket_knowledge_deflect(self, token, article_id, **kw):
        ticket = self._get_ticket_from_public_token(token)
        if not ticket:
            return request.not_found()
        article = request.env["document.page"].sudo().browse(article_id)
        if article.exists() and article._is_visible_for_portal(
            partner=ticket.commercial_partner_id,
            contract=ticket.support_contract_id,
            team=ticket.team_id,
        ):
            article._register_portal_deflection()
        return self._redirect_public_ticket(ticket, article_helped=1)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "helpdesk_knowledge_count" in counters:
            values["helpdesk_knowledge_count"] = len(self._get_visible_articles())
        return values

    def _prepare_public_ticket_values(self, ticket, **kwargs):
        values = super()._prepare_public_ticket_values(ticket, **kwargs)
        values.update(
            {
                "suggested_articles": self._get_suggested_articles(ticket),
            }
        )
        return values

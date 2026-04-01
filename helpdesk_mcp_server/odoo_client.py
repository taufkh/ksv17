"""
odoo_client.py
──────────────
Thin XML-RPC wrapper around Odoo.  Provides typed helpers used by the MCP
server so the server itself stays free of low-level RPC details.
"""

import os
import xmlrpc.client
from functools import cached_property
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class OdooClient:
    def __init__(
        self,
        url: str | None = None,
        db: str | None = None,
        username: str | None = None,
        password: str | None = None,
    ):
        self.url = (url or os.getenv("ODOO_URL", "http://localhost:8069")).rstrip("/")
        self.db = db or os.getenv("ODOO_DB", "")
        self.username = username or os.getenv("ODOO_USERNAME", "admin")
        self.password = password or os.getenv("ODOO_PASSWORD", "admin")
        self._uid: int | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    @cached_property
    def _common(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")

    @cached_property
    def _models(self):
        return xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    @property
    def uid(self) -> int:
        if self._uid is None:
            self._uid = self._common.authenticate(
                self.db, self.username, self.password, {}
            )
            if not self._uid:
                raise PermissionError(
                    f"Odoo authentication failed for user '{self.username}' "
                    f"on database '{self.db}' at {self.url}"
                )
        return self._uid

    def call(
        self,
        model: str,
        method: str,
        args: list,
        kwargs: dict | None = None,
    ) -> Any:
        return self._models.execute_kw(
            self.db, self.uid, self.password, model, method, args, kwargs or {}
        )

    # ── Ticket helpers ────────────────────────────────────────────────────────

    TICKET_FIELDS = [
        "id", "number", "name", "description",
        "partner_id", "partner_name", "partner_email",
        "team_id", "user_id", "stage_id", "category_id", "priority",
        "tag_ids",
        "ai_status", "ai_classification", "ai_confidence",
        "ai_summary", "ai_affected_modules", "ai_estimated_hours",
        "ai_response", "ai_dev_plan", "ai_analyzed_date",
        "create_date", "write_date", "closed", "closed_date",
    ]

    def search_tickets(
        self,
        domain: list | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "priority desc, create_date desc",
        fields: list | None = None,
    ) -> list[dict]:
        return self.call(
            "helpdesk.ticket",
            "search_read",
            [domain or []],
            {
                "fields": fields or self.TICKET_FIELDS,
                "limit": limit,
                "offset": offset,
                "order": order,
            },
        )

    def get_ticket(self, ticket_id: int) -> dict | None:
        results = self.call(
            "helpdesk.ticket",
            "search_read",
            [[["id", "=", ticket_id]]],
            {"fields": self.TICKET_FIELDS, "limit": 1},
        )
        return results[0] if results else None

    def get_ticket_by_number(self, number: str) -> dict | None:
        results = self.call(
            "helpdesk.ticket",
            "search_read",
            [[["number", "=", number]]],
            {"fields": self.TICKET_FIELDS, "limit": 1},
        )
        return results[0] if results else None

    def update_ticket(self, ticket_id: int, vals: dict) -> bool:
        return self.call("helpdesk.ticket", "write", [[ticket_id], vals])

    def trigger_ai_analysis(self, ticket_id: int) -> None:
        """Mark ticket as pending so the cron picks it up, or call directly."""
        self.update_ticket(ticket_id, {"ai_status": "pending"})

    # ── Chatter helpers ───────────────────────────────────────────────────────

    def get_ticket_messages(self, ticket_id: int, limit: int = 10) -> list[dict]:
        return self.call(
            "mail.message",
            "search_read",
            [[
                ["res_id", "=", ticket_id],
                ["model", "=", "helpdesk.ticket"],
                ["message_type", "in", ["comment", "email"]],
            ]],
            {
                "fields": [
                    "id", "date", "author_id", "body",
                    "message_type", "subtype_id",
                ],
                "limit": limit,
                "order": "date desc",
            },
        )

    def post_message(
        self,
        ticket_id: int,
        body: str,
        internal: bool = False,
    ) -> int:
        """Post a message to the ticket chatter. Returns message ID."""
        subtype = "mail.mt_note" if internal else "mail.mt_comment"
        return self.call(
            "helpdesk.ticket",
            "message_post",
            [ticket_id],
            {
                "body": body,
                "message_type": "comment",
                "subtype_xmlid": subtype,
            },
        )

    # ── Team helpers ──────────────────────────────────────────────────────────

    def list_teams(self) -> list[dict]:
        return self.call(
            "helpdesk.ticket.team",
            "search_read",
            [[]],
            {
                "fields": [
                    "id", "name", "ai_enabled", "ai_auto_reply",
                    "ai_project_context",
                ],
            },
        )

    def list_stages(self, team_id: int | None = None) -> list[dict]:
        domain = [["team_ids", "=", team_id]] if team_id else []
        return self.call(
            "helpdesk.ticket.stage",
            "search_read",
            [domain],
            {"fields": ["id", "name", "sequence", "closed", "team_ids"]},
        )

    # ── Stats helper ──────────────────────────────────────────────────────────

    def get_ai_stats(self) -> dict:
        """Return aggregate counts for the AI status dashboard."""
        all_statuses = [
            "pending", "processing", "answered", "dev_plan", "manual", "failed"
        ]
        stats = {}
        for status in all_statuses:
            count = self.call(
                "helpdesk.ticket",
                "search_count",
                [[["ai_status", "=", status]]],
            )
            stats[status] = count
        stats["total_analysed"] = self.call(
            "helpdesk.ticket",
            "search_count",
            [[["ai_analyzed_date", "!=", False]]],
        )
        return stats

#!/usr/bin/env python3
"""
Functional smoke test for custom Helpdesk API + public portal flows.

Run this script from inside the Odoo web container:
    python3 /mnt/extra-addons/docs/scripts/helpdesk_functional_smoke_test.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from urllib.parse import parse_qs, urlparse

import requests


def cleanup_ticket(db_name: str, ticket_id: int) -> bool:
    import odoo
    from odoo import SUPERUSER_ID, api
    from odoo.tools import config

    config["db_name"] = db_name
    registry = odoo.registry(db_name)
    with registry.cursor() as cr:
        env = api.Environment(cr, SUPERUSER_ID, {})
        ticket = env["helpdesk.ticket"].browse(ticket_id)
        if not ticket.exists():
            return True
        ticket.unlink()
        cr.commit()
    return True


def extract_public_token(public_portal_url: str) -> str:
    marker = "/helpdesk/track/"
    if marker not in public_portal_url:
        return ""
    return public_portal_url.split(marker, 1)[1].split("?", 1)[0]


def csrf_from_html(html: str) -> str:
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    return match.group(1) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Run functional smoke test for Helpdesk API + portal.")
    parser.add_argument("--base-url", default="http://localhost:8069")
    parser.add_argument("--db", default="ksv17-dev")
    parser.add_argument("--api-token", default="ksv17-demo-api-token")
    parser.add_argument("--reference-ticket", default="HT00001")
    parser.add_argument("--cleanup", action="store_true", default=True)
    parser.add_argument("--no-cleanup", action="store_false", dest="cleanup")
    args = parser.parse_args()

    session = requests.Session()
    headers = {"Authorization": f"Bearer {args.api_token}"}
    results: list[dict] = []

    def check(name: str, condition: bool, detail: dict) -> None:
        results.append({"name": name, "ok": bool(condition), "detail": detail})

    # This environment requires a DB-bound session before custom routes are reachable.
    resp = session.get(f"{args.base_url}/web", params={"db": args.db}, timeout=30, allow_redirects=True)
    check("db_session_init", resp.status_code == 200, {"status": resp.status_code, "url": resp.url})

    resp = session.get(f"{args.base_url}/api/helpdesk/v1/health", headers=headers, timeout=30)
    health = resp.json() if resp.ok else {}
    check(
        "api_health",
        resp.status_code == 200
        and health.get("ok") is True
        and health.get("data", {}).get("database") == args.db,
        {"status": resp.status_code, "body": health or resp.text[:300]},
    )

    resp = session.get(
        f"{args.base_url}/api/helpdesk/v1/tickets",
        params={"search": args.reference_ticket, "limit": 1},
        headers=headers,
        timeout=30,
    )
    listing = resp.json() if resp.ok else {}
    items = listing.get("data", {}).get("items", [])
    check(
        "api_reference_ticket_lookup",
        resp.status_code == 200 and listing.get("ok") is True and len(items) == 1,
        {"status": resp.status_code, "items_found": len(items)},
    )
    if not items:
        print(json.dumps({"results": results}, indent=2))
        return 1

    ref_ticket = items[0]
    ref_id = ref_ticket.get("id")
    ref_partner = (ref_ticket.get("partner") or {}).get("id")
    ref_category = (ref_ticket.get("category") or {}).get("id")
    ref_type = (ref_ticket.get("type") or {}).get("id")
    ref_team = (ref_ticket.get("team") or {}).get("id")

    # Negative path: empty reply must fail with validation_error.
    resp = session.post(
        f"{args.base_url}/api/helpdesk/v1/tickets/{ref_id}/reply",
        headers={**headers, "Content-Type": "application/json"},
        data="{}",
        timeout=30,
    )
    negative_reply = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    check(
        "api_reply_validation_error",
        resp.status_code == 400
        and negative_reply.get("ok") is False
        and negative_reply.get("error", {}).get("code") == "validation_error",
        {"status": resp.status_code, "body": negative_reply or resp.text[:300]},
    )

    # Positive path: create -> close via API -> reopen via public portal.
    unique = int(time.time())
    create_payload = {
        "name": f"[SMOKE-AUTO] Functional ticket {unique}",
        "description": "Auto smoke test ticket created by helpdesk_functional_smoke_test.py",
        "partner_id": ref_partner,
        "category_id": ref_category,
        "type_id": ref_type,
        "team_id": ref_team,
        "priority": "2",
    }
    resp = session.post(
        f"{args.base_url}/api/helpdesk/v1/tickets/create",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps(create_payload),
        timeout=30,
    )
    created = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    created_data = created.get("data", {})
    created_id = created_data.get("id")
    check(
        "api_create_smoke_ticket",
        resp.status_code == 201 and created.get("ok") is True and bool(created_id),
        {"status": resp.status_code, "ticket_id": created_id},
    )
    if not created_id:
        print(json.dumps({"results": results}, indent=2))
        return 1

    resp = session.post(
        f"{args.base_url}/api/helpdesk/v1/tickets/{created_id}/reply",
        headers={**headers, "Content-Type": "application/json"},
        data=json.dumps({"message": "Smoke auto reply message."}),
        timeout=30,
    )
    reply_body = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    check(
        "api_reply_smoke_ticket",
        resp.status_code == 200 and reply_body.get("ok") is True,
        {"status": resp.status_code},
    )

    resp = session.post(
        f"{args.base_url}/api/helpdesk/v1/tickets/{created_id}/close",
        headers={**headers, "Content-Type": "application/json"},
        data="{}",
        timeout=30,
    )
    close_body = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    check(
        "api_close_smoke_ticket",
        resp.status_code == 200
        and close_body.get("ok") is True
        and close_body.get("data", {}).get("closed") is True,
        {"status": resp.status_code},
    )

    public_url = close_body.get("data", {}).get("public_portal_url") or created_data.get("public_portal_url", "")
    portal_token = extract_public_token(public_url)
    query = parse_qs(urlparse(public_url).query)
    portal_db = (query.get("db") or [args.db])[0]
    check(
        "portal_public_url_present",
        bool(public_url) and bool(portal_token),
        {"public_url": public_url},
    )

    if portal_token:
        resp = session.get(f"{args.base_url}/helpdesk/track/{portal_token}", params={"db": portal_db}, timeout=30)
        csrf_token = csrf_from_html(resp.text)
        check(
            "portal_page_load",
            resp.status_code == 200 and bool(csrf_token),
            {"status": resp.status_code, "has_csrf": bool(csrf_token)},
        )
        if csrf_token:
            resp = session.post(
                f"{args.base_url}/helpdesk/track/{portal_token}/reopen",
                params={"db": portal_db},
                data={
                    "csrf_token": csrf_token,
                    "reopen_reason": "issue_not_resolved",
                    "reopen_detail": "Smoke test reopen validation.",
                    "confirm_reopen": "1",
                },
                timeout=30,
                allow_redirects=True,
            )
            check(
                "portal_reopen_smoke_ticket",
                resp.status_code == 200 and "reopen_success=1" in resp.url,
                {"status": resp.status_code, "url": resp.url},
            )

    if args.cleanup and created_id:
        try:
            removed = cleanup_ticket(args.db, int(created_id))
            check("cleanup_smoke_ticket", bool(removed), {"ticket_id": created_id})
        except Exception as exc:  # pragma: no cover - smoke utility guard
            check("cleanup_smoke_ticket", False, {"ticket_id": created_id, "error": str(exc)})

    print(json.dumps({"results": results}, indent=2))
    failed = [entry for entry in results if not entry["ok"]]
    if failed:
        print(json.dumps({"summary": "failed", "failed_count": len(failed)}, indent=2))
        return 1
    print(json.dumps({"summary": "passed", "checks": len(results)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

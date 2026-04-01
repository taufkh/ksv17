from odoo import SUPERUSER_ID, api, fields


def _get_or_create_problem(env, values):
    problem = env["helpdesk.problem"].search([("name", "=", values["name"])], limit=1)
    if problem:
        problem.write(values)
        return problem
    return env["helpdesk.problem"].create(values)


def post_init_hook(env):
    env = api.Environment(
        env.cr,
        SUPERUSER_ID,
        {
            "tracking_disable": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
        },
    )

    ticket_model = env["helpdesk.ticket"]
    article_model = env["document.page"]
    asset_model = env["helpdesk.support.asset"]

    tickets = {
        ticket.name: ticket
        for ticket in ticket_model.search(
            [("name", "in", [
                "[DEMO] POS sync error after patch",
                "[DEMO] POS sync error after patch (duplicate)",
                "[DEMO] Cannot post invoice to customer",
            ])]
        )
    }
    articles = {
        article.name: article
        for article in article_model.search(
            [("name", "in", [
                "[DEMO] POS sync diagnostic checklist",
                "[DEMO] Invoice posting blocked after March patch",
            ])]
        )
    }
    assets = {
        asset.name: asset
        for asset in asset_model.search(
            [("name", "in", [
                "[DEMO] Branch A POS Terminal 03",
                "[DEMO] Finance HQ Billing Workflow",
            ])]
        )
    }

    pos_problem = _get_or_create_problem(
        env,
        {
            "name": "[DEMO] POS Sync Timeout After March Patch",
            "state": "known_error",
            "severity": "critical",
            "known_error": True,
            "detected_date": fields.Date.from_string("2026-03-19"),
            "problem_owner_id": env.ref("base.user_admin").id,
            "partner_id": tickets.get("[DEMO] POS sync error after patch").commercial_partner_id.id
            if tickets.get("[DEMO] POS sync error after patch")
            else False,
            "team_id": tickets.get("[DEMO] POS sync error after patch").team_id.id
            if tickets.get("[DEMO] POS sync error after patch")
            else False,
            "support_asset_id": assets.get("[DEMO] Branch A POS Terminal 03").id
            if assets.get("[DEMO] Branch A POS Terminal 03")
            else False,
            "knowledge_article_id": articles.get("[DEMO] POS sync diagnostic checklist").id
            if articles.get("[DEMO] POS sync diagnostic checklist")
            else False,
            "impact_summary": (
                "Branch checkout synchronization fails during network latency spikes, causing queue delays and risk of duplicate retries."
            ),
            "root_cause_summary": (
                "The March patch introduced a timeout threshold that is too aggressive for branch environments with unstable network latency."
            ),
            "workaround": (
                "<p>Apply the temporary retry timeout configuration and monitor queue growth during peak hours.</p>"
            ),
            "permanent_fix_plan": (
                "<p>Release a patched timeout profile and validate it in one branch before wider rollout.</p>"
            ),
        },
    )

    invoice_problem = _get_or_create_problem(
        env,
        {
            "name": "[DEMO] Invoice Posting Validation Regression",
            "state": "investigating",
            "severity": "high",
            "known_error": False,
            "detected_date": fields.Date.from_string("2026-03-24"),
            "problem_owner_id": env.ref("base.user_admin").id,
            "partner_id": tickets.get("[DEMO] Cannot post invoice to customer").commercial_partner_id.id
            if tickets.get("[DEMO] Cannot post invoice to customer")
            else False,
            "team_id": tickets.get("[DEMO] Cannot post invoice to customer").team_id.id
            if tickets.get("[DEMO] Cannot post invoice to customer")
            else False,
            "support_asset_id": assets.get("[DEMO] Finance HQ Billing Workflow").id
            if assets.get("[DEMO] Finance HQ Billing Workflow")
            else False,
            "knowledge_article_id": articles.get("[DEMO] Invoice posting blocked after March patch").id
            if articles.get("[DEMO] Invoice posting blocked after March patch")
            else False,
            "impact_summary": (
                "Finance users are blocked from posting invoices to customers after the March patch validation changes."
            ),
            "root_cause_summary": "Validation regression is still under analysis.",
            "workaround": (
                "<p>Use the validated temporary posting path while the permanent fix is still under investigation.</p>"
            ),
            "permanent_fix_plan": (
                "<p>Confirm the failing validation branch and ship a targeted patch after reproducing it in staging.</p>"
            ),
        },
    )

    for name in [
        "[DEMO] POS sync error after patch",
        "[DEMO] POS sync error after patch (duplicate)",
    ]:
        ticket = tickets.get(name)
        if ticket and pos_problem:
            ticket.write({"problem_id": pos_problem.id})

    ticket = tickets.get("[DEMO] Cannot post invoice to customer")
    if ticket and invoice_problem:
        ticket.write({"problem_id": invoice_problem.id})

    env.cr.commit()

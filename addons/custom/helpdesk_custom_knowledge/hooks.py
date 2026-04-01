from odoo import SUPERUSER_ID, api, fields


def _get_or_create_category(page_model, name, parent=False, company_id=False):
    domain = [("name", "=", name), ("type", "=", "category"), ("is_helpdesk_article", "=", True)]
    if parent:
        domain.append(("parent_id", "=", parent.id))
    else:
        domain.append(("parent_id", "=", False))
    category = page_model.search(domain, limit=1)
    vals = {
        "name": name,
        "type": "category",
        "is_helpdesk_article": True,
        "article_status": "internal",
        "company_id": company_id,
        "parent_id": parent.id if parent else False,
    }
    if category:
        category.write(vals)
        return category
    return page_model.create(vals)


def _get_or_create_page(page_model, values):
    page = page_model.search(
        [("name", "=", values["name"]), ("type", "=", "content"), ("is_helpdesk_article", "=", True)],
        limit=1,
    )
    if page:
        page.write(values)
        return page
    return page_model.create(values)


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

    page_model = env["document.page"]
    admin_user = env.ref("base.user_admin")
    company = env.company

    root = _get_or_create_category(
        page_model,
        "[HELPDESK] Support Knowledge",
        company_id=company.id,
    )
    billing_category = _get_or_create_category(
        page_model,
        "[HELPDESK] Billing & Finance",
        parent=root,
        company_id=company.id,
    )
    access_category = _get_or_create_category(
        page_model,
        "[HELPDESK] Access & Identity",
        parent=root,
        company_id=company.id,
    )
    pos_category = _get_or_create_category(
        page_model,
        "[HELPDESK] POS & Sync",
        parent=root,
        company_id=company.id,
    )

    tickets = {
        ticket.name: ticket
        for ticket in env["helpdesk.ticket"].search(
            [("name", "in", [
                "[DEMO] Cannot post invoice to customer",
                "[DEMO] Need new portal access for branch manager",
                "[DEMO] POS sync error after patch",
                "[DEMO] POS sync error after patch (duplicate)",
            ])]
        )
    }

    invoice_ticket = tickets.get("[DEMO] Cannot post invoice to customer")
    portal_ticket = tickets.get("[DEMO] Need new portal access for branch manager")
    pos_ticket = tickets.get("[DEMO] POS sync error after patch")
    pos_dup_ticket = tickets.get("[DEMO] POS sync error after patch (duplicate)")

    if invoice_ticket:
        page = _get_or_create_page(
            page_model,
            {
                "name": "[DEMO] Invoice posting blocked after March patch",
                "type": "content",
                "parent_id": billing_category.id,
                "company_id": company.id,
                "draft_name": "1.0",
                "draft_summary": "Initial troubleshooting guide",
                "is_helpdesk_article": True,
                "article_status": "internal",
                "resolution_pattern": "fix",
                "article_owner_id": admin_user.id,
                "review_due_date": fields.Date.today(),
                "helpdesk_primary_ticket_id": invoice_ticket.id,
                "helpdesk_ticket_ids": [(6, 0, [invoice_ticket.id])],
                "content": """
                    <h2>Symptoms</h2>
                    <p>Posting invoice fails after the March patch with a validation error.</p>
                    <h2>Checks</h2>
                    <ol>
                        <li>Confirm the affected customer and invoice draft number.</li>
                        <li>Check whether fiscal position and account mapping changed after the patch.</li>
                        <li>Review server logs for the exact validation message.</li>
                    </ol>
                    <h2>Workaround</h2>
                    <p>Recompute invoice lines, verify journal mapping, then retry posting after cache refresh.</p>
                    <h2>Escalation Rule</h2>
                    <p>If month-end closure is blocked, escalate to finance support lead immediately.</p>
                """,
            },
        )
        page.action_mark_internal()

    if portal_ticket:
        page = _get_or_create_page(
            page_model,
            {
                "name": "[DEMO] Branch manager portal access checklist",
                "type": "content",
                "parent_id": access_category.id,
                "company_id": company.id,
                "draft_name": "1.0",
                "draft_summary": "Portal onboarding checklist",
                "is_helpdesk_article": True,
                "article_status": "portal_ready",
                "resolution_pattern": "process",
                "article_owner_id": admin_user.id,
                "review_due_date": fields.Date.today(),
                "helpdesk_primary_ticket_id": portal_ticket.id,
                "helpdesk_ticket_ids": [(6, 0, [portal_ticket.id])],
                "content": """
                    <h2>Scope</h2>
                    <p>Grant portal access for a branch manager without exposing other branch records.</p>
                    <h2>Checklist</h2>
                    <ol>
                        <li>Validate contact email and branch ownership.</li>
                        <li>Confirm portal group assignment.</li>
                        <li>Test the public tracking link and ticket visibility.</li>
                        <li>Log the completion note in the ticket chatter.</li>
                    </ol>
                    <h2>Customer Guidance</h2>
                    <p>Share the portal URL, first login steps, and attachment upload limits.</p>
                """,
            },
        )
        page.action_mark_portal_ready()

    if pos_ticket:
        linked_ids = [ticket.id for ticket in [pos_ticket, pos_dup_ticket] if ticket]
        page = _get_or_create_page(
            page_model,
            {
                "name": "[DEMO] POS sync diagnostic checklist",
                "type": "content",
                "parent_id": pos_category.id,
                "company_id": company.id,
                "draft_name": "1.0",
                "draft_summary": "Operational checklist for sync incidents",
                "is_helpdesk_article": True,
                "article_status": "internal",
                "resolution_pattern": "workaround",
                "article_owner_id": admin_user.id,
                "review_due_date": fields.Date.today(),
                "helpdesk_primary_ticket_id": pos_ticket.id,
                "helpdesk_ticket_ids": [(6, 0, linked_ids)],
                "content": """
                    <h2>When to Use</h2>
                    <p>Use this checklist when POS transactions are not syncing to the central database.</p>
                    <h2>Diagnostic Steps</h2>
                    <ol>
                        <li>Validate branch connectivity and local device time.</li>
                        <li>Check queue backlog and failed payload count.</li>
                        <li>Compare duplicate transaction references against central logs.</li>
                        <li>Restart sync service only after preserving pending queue evidence.</li>
                    </ol>
                    <h2>Temporary Workaround</h2>
                    <p>Switch branch to offline-safe mode and capture manual reconciliation batch at end of shift.</p>
                """,
            },
        )
        page.action_mark_internal()

    env.cr.commit()


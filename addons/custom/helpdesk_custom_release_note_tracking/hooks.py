from datetime import date

from odoo import SUPERUSER_ID, api


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

    problems = {
        record.name: record
        for record in env["helpdesk.problem"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] POS Sync Timeout After March Patch",
                        "[DEMO] Invoice Posting Validation Regression",
                    ],
                )
            ]
        )
    }
    articles = {
        record.name: record
        for record in env["document.page"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] POS sync diagnostic checklist",
                        "[DEMO] Invoice posting blocked after March patch",
                    ],
                )
            ]
        )
    }
    tickets = {
        record.name: record
        for record in env["helpdesk.ticket"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] POS sync error after patch",
                        "[DEMO] POS sync error after patch (duplicate)",
                        "[DEMO] Cannot post invoice to customer",
                    ],
                )
            ]
        )
    }

    release_model = env["helpdesk.release.note"]

    pos_note = release_model.search(
        [("name", "=", "[DEMO] POS Timeout Stabilization Hotfix")], limit=1
    )
    if not pos_note:
        pos_note = release_model.create(
            {
                "name": "[DEMO] POS Timeout Stabilization Hotfix",
                "version": "2026.03.29-hotfix-01",
                "release_type": "hotfix",
                "state": "communicated",
                "severity": "critical",
                "release_date": date(2026, 3, 29),
                "communication_due_date": date(2026, 3, 29),
                "team_id": problems["[DEMO] POS Sync Timeout After March Patch"].team_id.id,
                "owner_id": problems["[DEMO] POS Sync Timeout After March Patch"].problem_owner_id.id,
                "summary": "Hotfix rollout for branch POS sync timeout after the March patch.",
                "technical_notes": "<p>Adjusted timeout handling and retried synchronization handshake validation.</p>",
                "rollout_notes": "<p>Deploy hotfix to affected branches first, then monitor timeout metrics for 24 hours.</p>",
                "customer_message": "<p>We deployed a stabilization hotfix for the POS synchronization timeout. Please retry branch sync and report any residual issue.</p>",
                "problem_ids": [
                    (
                        6,
                        0,
                        [problems["[DEMO] POS Sync Timeout After March Patch"].id],
                    )
                ],
                "ticket_ids": [
                    (
                        6,
                        0,
                        [
                            tickets["[DEMO] POS sync error after patch"].id,
                            tickets["[DEMO] POS sync error after patch (duplicate)"].id,
                        ],
                    )
                ],
                "knowledge_article_ids": [
                    (6, 0, [articles["[DEMO] POS sync diagnostic checklist"].id])
                ],
            }
        )

    invoice_note = release_model.search(
        [("name", "=", "[DEMO] Invoice Validation Regression Patch Note")], limit=1
    )
    if not invoice_note:
        invoice_note = release_model.create(
            {
                "name": "[DEMO] Invoice Validation Regression Patch Note",
                "version": "2026.03.30-patch-02",
                "release_type": "patch",
                "state": "rolled_out",
                "severity": "high",
                "release_date": date(2026, 3, 30),
                "communication_due_date": date(2026, 3, 30),
                "team_id": problems["[DEMO] Invoice Posting Validation Regression"].team_id.id,
                "owner_id": problems["[DEMO] Invoice Posting Validation Regression"].problem_owner_id.id,
                "summary": "Patch note for invoice posting validation regression introduced after the March patch.",
                "technical_notes": "<p>Corrected invoice validation branch logic and restored legacy safeguard for billing flow.</p>",
                "rollout_notes": "<p>Deploy after accounting smoke test and announce only when post-patch verification is complete.</p>",
                "customer_message": "<p>The invoice posting validation issue has been corrected and the patch is now available for verification.</p>",
                "problem_ids": [
                    (
                        6,
                        0,
                        [problems["[DEMO] Invoice Posting Validation Regression"].id],
                    )
                ],
                "ticket_ids": [
                    (
                        6,
                        0,
                        [tickets["[DEMO] Cannot post invoice to customer"].id],
                    )
                ],
                "knowledge_article_ids": [
                    (
                        6,
                        0,
                        [articles["[DEMO] Invoice posting blocked after March patch"].id],
                    )
                ],
            }
        )

    for release_note in (pos_note, invoice_note):
        for ticket in release_note.ticket_ids:
            existing = ticket.communication_log_ids.filtered(
                lambda log: log.release_note_id == release_note
                and log.subject == release_note.name
            )
            if not existing:
                ticket._create_communication_log(
                    channel="manual",
                    direction="outbound",
                    communication_type="status_change",
                    status="done",
                    subject=release_note.name,
                    summary=release_note.summary,
                    body=release_note.customer_message,
                    partner=ticket.partner_id,
                    user=release_note.owner_id,
                    source_model=release_note._name,
                    source_res_id=release_note.id,
                    release_note=release_note,
                )

    env.cr.commit()

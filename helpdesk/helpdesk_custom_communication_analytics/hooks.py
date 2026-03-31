from datetime import datetime

from odoo import SUPERUSER_ID, api, fields


def _dt(value):
    return fields.Datetime.to_string(datetime.fromisoformat(value))


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

    tickets = {
        ticket.name: ticket
        for ticket in env["helpdesk.ticket"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] Cannot post invoice to customer",
                        "[DEMO] Need new portal access for branch manager",
                        "[DEMO] POS sync error after patch",
                        "[DEMO] Legacy ticket awaiting customer reply",
                        "[DEMO] CRM lead follow-up from support case",
                    ],
                )
            ]
        )
    }

    demo_rows = [
        (
            "[DEMO] Cannot post invoice to customer",
            {
                "channel": "whatsapp",
                "direction": "outbound",
                "communication_type": "notification",
                "status": "sent",
                "subject": "[DEMO] WhatsApp update on invoice issue",
                "summary": "Support sent a customer update and expected fix timeline.",
                "body": "We have reproduced the issue and scheduled the patch validation.",
                "logged_at": _dt("2026-03-29T10:20:00"),
            },
        ),
        (
            "[DEMO] Need new portal access for branch manager",
            {
                "channel": "email",
                "direction": "outbound",
                "communication_type": "follow_up",
                "status": "done",
                "subject": "[DEMO] Access activation instructions sent",
                "summary": "Support emailed the activation steps to the branch manager.",
                "body": "Activation steps and temporary password reset instructions were sent by email.",
                "logged_at": _dt("2026-03-29T16:15:00"),
            },
        ),
        (
            "[DEMO] POS sync error after patch",
            {
                "channel": "whatsapp",
                "direction": "outbound",
                "communication_type": "notification",
                "status": "failed",
                "subject": "[DEMO] Failed WhatsApp stabilization update",
                "summary": "One outbound update failed due to invalid destination number format.",
                "body": "The first outbound WhatsApp notification failed before the number was corrected.",
                "logged_at": _dt("2026-03-27T10:05:00"),
            },
        ),
        (
            "[DEMO] Legacy ticket awaiting customer reply",
            {
                "channel": "email",
                "direction": "outbound",
                "communication_type": "follow_up",
                "status": "done",
                "subject": "[DEMO] Reminder sent to customer",
                "summary": "Support sent an email reminder because the customer had not responded for several days.",
                "body": "Reminder sent asking whether the issue could be closed or still required attention.",
                "logged_at": _dt("2026-03-29T08:00:00"),
            },
        ),
        (
            "[DEMO] CRM lead follow-up from support case",
            {
                "channel": "api",
                "direction": "inbound",
                "communication_type": "customer_update",
                "status": "done",
                "subject": "[DEMO] External system synced follow-up note",
                "summary": "An external integration pushed a customer follow-up note through the API.",
                "body": "CRM sync confirmed the customer is waiting for a commercial review after support closure.",
                "logged_at": _dt("2026-03-29T13:40:00"),
            },
        ),
    ]

    for ticket_name, values in demo_rows:
        ticket = tickets.get(ticket_name)
        if not ticket:
            continue
        if ticket.communication_log_ids.filtered(lambda log: log.subject == values["subject"]):
            continue
        ticket._create_communication_log(**values)

    env.cr.commit()

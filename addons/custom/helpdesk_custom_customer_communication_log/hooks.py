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
            [("name", "in", [
                "[DEMO] Cannot post invoice to customer",
                "[DEMO] Need new portal access for branch manager",
                "[DEMO] POS sync error after patch",
                "[DEMO] Legacy ticket awaiting customer reply",
            ])]
        )
    }

    if tickets.get("[DEMO] Cannot post invoice to customer"):
        tickets["[DEMO] Cannot post invoice to customer"]._create_communication_log(
            channel="email",
            direction="inbound",
            communication_type="customer_update",
            status="done",
            subject="[DEMO] Customer shared validation screenshot",
            summary="Customer sent an email update confirming the invoice error still happens after the March patch.",
            body="Customer attached validation screenshots and asked for an ETA on the permanent fix.",
            logged_at=_dt("2026-03-29T09:10:00"),
        )

    if tickets.get("[DEMO] Need new portal access for branch manager"):
        tickets["[DEMO] Need new portal access for branch manager"]._create_communication_log(
            channel="portal",
            direction="inbound",
            communication_type="feedback",
            status="done",
            subject="[DEMO] Portal feedback from branch manager",
            summary="Customer confirmed the portal onboarding steps but requested a shorter access checklist.",
            body="Portal feedback noted that the branch manager could log in successfully after onboarding.",
            logged_at=_dt("2026-03-29T15:42:00"),
        )

    if tickets.get("[DEMO] POS sync error after patch"):
        tickets["[DEMO] POS sync error after patch"]._create_communication_log(
            channel="whatsapp",
            direction="outbound",
            communication_type="notification",
            status="sent",
            subject="[DEMO] WhatsApp escalation update",
            summary="WhatsApp alert sent to customer contact about the on-site stabilization and pending permanent patch.",
            body="Branch team was informed that the temporary timeout adjustment had been applied successfully.",
            logged_at=_dt("2026-03-27T11:30:00"),
        )

    if tickets.get("[DEMO] Legacy ticket awaiting customer reply"):
        tickets["[DEMO] Legacy ticket awaiting customer reply"]._create_communication_log(
            channel="phone",
            direction="outbound",
            communication_type="follow_up",
            status="done",
            subject="[DEMO] Manual phone follow-up",
            summary="Support agent called the customer to ask whether the issue is still open and waiting for a response.",
            body="Phone follow-up completed; customer promised to respond with an update the next morning.",
            logged_at=_dt("2026-03-28T16:15:00"),
        )

    env.cr.commit()

from datetime import datetime

from odoo import SUPERUSER_ID, api, fields


def _get_or_create_dispatch(env, values):
    dispatch = env["helpdesk.dispatch"].search(
        [("ticket_id", "=", values["ticket_id"]), ("name", "=", values["name"])],
        limit=1,
    )
    if dispatch:
        dispatch.write(values)
        return dispatch
    return env["helpdesk.dispatch"].create(values)


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

    admin_user = env.ref("base.user_admin")
    demo_support = env["res.users"].search(
        [("login", "=", "support.demo@example.com")],
        limit=1,
    )
    engineer = demo_support or admin_user

    def ticket_by_name(name):
        return env["helpdesk.ticket"].search([("name", "=", name)], limit=1)

    def approval_by_name(ticket, name):
        if not ticket:
            return env["helpdesk.ticket.approval"]
        return env["helpdesk.ticket.approval"].search(
            [("ticket_id", "=", ticket.id), ("name", "=", name)],
            limit=1,
        )

    ticket_pos = ticket_by_name("[DEMO] POS sync error after patch")
    if ticket_pos:
        _get_or_create_dispatch(
            env,
            {
                "name": "[DEMO] Emergency POS Branch Visit",
                "ticket_id": ticket_pos.id,
                "engineer_id": engineer.id,
                "dispatch_type": "onsite_visit",
                "urgency": "urgent",
                "state": "completed",
                "scheduled_start": _dt("2026-03-27T09:00:00"),
                "scheduled_end": _dt("2026-03-27T11:00:00"),
                "actual_start": _dt("2026-03-27T09:12:00"),
                "actual_end": _dt("2026-03-27T11:18:00"),
                "location": "Nusantara Retail Branch A",
                "site_contact_name": "[DEMO] Rina Portal",
                "site_contact_phone": "+62-811-1111-0001",
                "travel_required": True,
                "resolution_status": "temporary_fix",
                "work_summary": (
                    "<p>Engineer validated the sync issue on-site, captured logs, "
                    "and applied a temporary retry configuration to stabilize transactions.</p>"
                ),
                "visit_findings": (
                    "<p>Issue reproduced when the store network latency exceeded the patch timeout threshold.</p>"
                ),
                "followup_required": True,
                "followup_action": "Monitor branch sync performance for the next 48 hours.",
            },
        )

    ticket_finance = ticket_by_name("[DEMO] Cannot post invoice to customer")
    if ticket_finance:
        _get_or_create_dispatch(
            env,
            {
                "name": "[DEMO] Finance Workflow Validation Session",
                "ticket_id": ticket_finance.id,
                "engineer_id": admin_user.id,
                "dispatch_type": "remote_session",
                "urgency": "high",
                "state": "scheduled",
                "scheduled_start": _dt("2026-03-29T10:00:00"),
                "scheduled_end": _dt("2026-03-29T12:00:00"),
                "location": "Remote session with finance team",
                "site_contact_name": "[DEMO] Bimo Finance",
                "site_contact_phone": "+62-811-1111-0002",
                "travel_required": False,
                "resolution_status": "pending",
                "work_summary": (
                    "<p>Remote walkthrough booked to validate the invoice posting error "
                    "and confirm the exact user flow before the next patch window.</p>"
                ),
            },
        )

    ticket_access = ticket_by_name("[DEMO] Need new portal access for branch manager")
    if ticket_access:
        _get_or_create_dispatch(
            env,
            {
                "name": "[DEMO] Branch Manager Portal Onboarding",
                "ticket_id": ticket_access.id,
                "engineer_id": engineer.id,
                "dispatch_type": "onsite_visit",
                "urgency": "normal",
                "state": "scheduled",
                "scheduled_start": _dt("2026-03-30T13:00:00"),
                "scheduled_end": _dt("2026-03-30T14:30:00"),
                "location": "Nusantara Retail HQ",
                "site_contact_name": "[DEMO] Rina Portal",
                "site_contact_phone": "+62-811-1111-0001",
                "travel_required": True,
                "approval_id": approval_by_name(
                    ticket_access, "[DEMO] Access exception approval"
                ).id,
                "resolution_status": "pending",
                "work_summary": (
                    "<p>Scheduled branch onboarding visit to validate portal role access "
                    "and complete the final user handover checklist.</p>"
                ),
            },
        )

    ticket_followup = ticket_by_name("[DEMO] CRM lead follow-up from support case")
    if ticket_followup:
        _get_or_create_dispatch(
            env,
            {
                "name": "[DEMO] Discovery Visit Follow-up",
                "ticket_id": ticket_followup.id,
                "engineer_id": engineer.id,
                "dispatch_type": "inspection",
                "urgency": "normal",
                "state": "no_access",
                "scheduled_start": _dt("2026-03-28T14:00:00"),
                "scheduled_end": _dt("2026-03-28T16:00:00"),
                "actual_start": _dt("2026-03-28T14:25:00"),
                "actual_end": _dt("2026-03-28T14:40:00"),
                "location": "Customer branch warehouse",
                "site_contact_name": "[DEMO] Rina Portal",
                "site_contact_phone": "+62-811-1111-0001",
                "travel_required": True,
                "approval_id": approval_by_name(
                    ticket_followup, "[DEMO] Onsite visit approval"
                ).id,
                "resolution_status": "follow_up",
                "work_summary": (
                    "<p>Engineer arrived on site, but the customer contact was unavailable and the branch room was locked.</p>"
                ),
                "visit_findings": (
                    "<p>No system validation could be performed because the branch team was not ready for the appointment.</p>"
                ),
                "followup_required": True,
                "followup_action": "Reschedule after customer confirms branch readiness.",
            },
        )

    env.cr.commit()

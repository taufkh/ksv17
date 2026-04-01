from datetime import datetime

from odoo import SUPERUSER_ID, api, fields


PNG_1PX = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAgMBgJ0nXwAAAABJRU5ErkJggg=="
)


def _dt(value):
    return fields.Datetime.to_string(datetime.fromisoformat(value))


def _get_or_create_evidence(env, dispatch, values):
    evidence = env["helpdesk.dispatch.evidence"].search(
        [("dispatch_id", "=", dispatch.id), ("name", "=", values["name"])],
        limit=1,
    )
    if evidence:
        evidence.write(values)
        return evidence
    return env["helpdesk.dispatch.evidence"].create(dict(values, dispatch_id=dispatch.id))


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

    demo_dispatches = {
        "[DEMO] Emergency POS Branch Visit": {
            "travel_start_at": _dt("2026-03-27T08:20:00"),
            "arrival_at": _dt("2026-03-27T09:35:00"),
            "departure_at": _dt("2026-03-27T11:10:00"),
            "pre_departure_customer_confirmed": True,
            "pre_departure_tools_ready": True,
            "pre_departure_scope_confirmed": True,
            "pre_departure_asset_checked": True,
            "onsite_access_confirmed": True,
            "onsite_issue_validated": True,
            "onsite_customer_briefed": True,
            "onsite_work_documented": True,
            "customer_signoff_required": True,
            "signoff_status": "signed",
            "signoff_contact_name": "[DEMO] Rina Portal",
            "signoff_contact_role": "Branch Operations Lead",
            "signoff_notes": "Temporary stabilization accepted while waiting for the permanent patch.",
            "signoff_at": _dt("2026-03-27T11:22:00"),
        },
        "[DEMO] Discovery Visit Follow-up": {
            "travel_start_at": _dt("2026-03-28T13:10:00"),
            "arrival_at": _dt("2026-03-28T14:05:00"),
            "departure_at": _dt("2026-03-28T14:30:00"),
            "pre_departure_customer_confirmed": True,
            "pre_departure_tools_ready": True,
            "pre_departure_scope_confirmed": True,
            "pre_departure_asset_checked": True,
            "customer_signoff_required": False,
            "signoff_status": "not_required",
            "signoff_notes": "No sign-off collected because the site contact was unavailable.",
        },
        "[DEMO] Finance Workflow Validation Session": {
            "pre_departure_customer_confirmed": True,
            "pre_departure_tools_ready": True,
            "pre_departure_scope_confirmed": False,
            "pre_departure_asset_checked": True,
            "customer_signoff_required": True,
            "signoff_status": "pending",
        },
    }

    for dispatch in env["helpdesk.dispatch"].search([("name", "in", list(demo_dispatches.keys()))]):
        dispatch.write(demo_dispatches[dispatch.name])

    pos_dispatch = env["helpdesk.dispatch"].search(
        [("name", "=", "[DEMO] Emergency POS Branch Visit")],
        limit=1,
    )
    if pos_dispatch:
        _get_or_create_evidence(
            env,
            pos_dispatch,
            {
                "name": "[DEMO] POS arrival photo",
                "evidence_type": "arrival_photo",
                "capture_stage": "arrival",
                "captured_on": _dt("2026-03-27T09:36:00"),
                "file_data": PNG_1PX,
                "file_name": "pos-arrival.png",
                "note": "Engineer arrival snapshot at the branch entrance.",
            },
        )
        _get_or_create_evidence(
            env,
            pos_dispatch,
            {
                "name": "[DEMO] POS sync diagnostic screenshot",
                "evidence_type": "work_in_progress",
                "capture_stage": "on_site",
                "captured_on": _dt("2026-03-27T10:08:00"),
                "file_data": PNG_1PX,
                "file_name": "pos-diagnostic.png",
                "note": "Queue timeout captured during on-site troubleshooting.",
            },
        )
        _get_or_create_evidence(
            env,
            pos_dispatch,
            {
                "name": "[DEMO] POS customer sign-off proof",
                "evidence_type": "customer_signoff",
                "capture_stage": "signoff",
                "captured_on": _dt("2026-03-27T11:22:00"),
                "file_data": PNG_1PX,
                "file_name": "pos-signoff.png",
                "note": "Customer sign-off receipt captured after temporary stabilization.",
            },
        )

    no_access_dispatch = env["helpdesk.dispatch"].search(
        [("name", "=", "[DEMO] Discovery Visit Follow-up")],
        limit=1,
    )
    if no_access_dispatch:
        _get_or_create_evidence(
            env,
            no_access_dispatch,
            {
                "name": "[DEMO] Locked warehouse access photo",
                "evidence_type": "site_access",
                "capture_stage": "arrival",
                "captured_on": _dt("2026-03-28T14:08:00"),
                "file_data": PNG_1PX,
                "file_name": "warehouse-no-access.png",
                "note": "Site access was blocked when the engineer arrived.",
            },
        )

    env.cr.commit()

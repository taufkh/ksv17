from datetime import datetime

from odoo import SUPERUSER_ID, api, fields


def _dt(value):
    return fields.Datetime.to_string(datetime.fromisoformat(value))


def _get_or_create_report(env, dispatch, values):
    report = env["helpdesk.field.service.report"].search(
        [("dispatch_id", "=", dispatch.id), ("name", "=", values["name"])],
        limit=1,
    )
    if report:
        report.write(values)
        return report
    return env["helpdesk.field.service.report"].create(
        dict(values, dispatch_id=dispatch.id)
    )


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

    dispatch_pos = env["helpdesk.dispatch"].search(
        [("name", "=", "[DEMO] Emergency POS Branch Visit")],
        limit=1,
    )
    if dispatch_pos:
        _get_or_create_report(
            env,
            dispatch_pos,
            {
                "name": "[DEMO] POS Branch Visit Report",
                "service_date": _dt("2026-03-27T11:18:00"),
                "visit_outcome": "partial_restore",
                "state": "acknowledged",
                "executive_summary": (
                    "<p>The branch sync issue was reproduced on site and stabilized with "
                    "a temporary timeout adjustment. Permanent patch confirmation is still required.</p>"
                ),
                "issue_confirmed": True,
                "environment_checked": True,
                "logs_collected": True,
                "customer_briefed": True,
                "safety_check_completed": True,
                "resolution_confirmed": False,
                "root_cause": (
                    "The March patch introduced a timeout threshold that fails when branch "
                    "network latency spikes during queue synchronization."
                ),
                "actions_performed": (
                    "<ul>"
                    "<li>Validated sync failure on the branch workstation.</li>"
                    "<li>Collected application and queue retry logs.</li>"
                    "<li>Applied a temporary retry timeout configuration.</li>"
                    "<li>Coached the branch lead on monitoring steps.</li>"
                    "</ul>"
                ),
                "parts_used": "No hardware parts used. Temporary configuration change only.",
                "recommendations": (
                    "Monitor for 48 hours, confirm no duplicate queue entries, and deploy the "
                    "follow-up patch in the next maintenance window."
                ),
                "followup_required": True,
                "next_steps": "Helpdesk engineering to release the permanent timeout patch.",
                "customer_contact_name": "[DEMO] Rina Portal",
                "customer_contact_role": "Branch Operations Lead",
                "customer_feedback": (
                    "Temporary fix accepted. Customer asked for a permanent patch confirmation "
                    "before weekend peak hours."
                ),
                "customer_acknowledged": True,
                "acknowledgement_date": _dt("2026-03-27T11:25:00"),
            },
        )

    dispatch_no_access = env["helpdesk.dispatch"].search(
        [("name", "=", "[DEMO] Discovery Visit Follow-up")],
        limit=1,
    )
    if dispatch_no_access:
        _get_or_create_report(
            env,
            dispatch_no_access,
            {
                "name": "[DEMO] Warehouse Discovery No Access Report",
                "service_date": _dt("2026-03-28T14:40:00"),
                "visit_outcome": "no_access",
                "state": "submitted",
                "executive_summary": (
                    "<p>The scheduled discovery visit could not proceed because the customer "
                    "contact was unavailable and the warehouse access room remained locked.</p>"
                ),
                "issue_confirmed": False,
                "environment_checked": False,
                "logs_collected": False,
                "customer_briefed": False,
                "safety_check_completed": True,
                "resolution_confirmed": False,
                "root_cause": "Site access and customer readiness were not confirmed before dispatch.",
                "actions_performed": (
                    "<p>Engineer verified arrival on site, attempted customer contact, and documented "
                    "the blocked access condition for follow-up rescheduling.</p>"
                ),
                "recommendations": (
                    "Require customer readiness confirmation and site access approval at least one day "
                    "before the next dispatch."
                ),
                "followup_required": True,
                "next_steps": "Reschedule discovery visit after customer confirms branch availability.",
                "customer_contact_name": "[DEMO] Rina Portal",
                "customer_contact_role": "Operations Coordinator",
            },
        )

    env.cr.commit()

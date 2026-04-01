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

    playbook_model = env["helpdesk.customer.success.playbook"]
    contract_model = env["helpdesk.support.contract"]
    partner_model = env["res.partner"]

    demo_specs = [
        {
            "partner_name": "[DEMO] PT Arunika Logistik",
            "name": "[DEMO] Gold Customer Monthly Success Review",
            "playbook_type": "quarterly_review",
            "health_state": "watch",
            "next_action_date": date(2026, 3, 31),
            "success_goal": "Protect support satisfaction and prepare April renewal conversation.",
            "risk_note": "Ticket volume is manageable, but the renewal pack needs stakeholder alignment.",
            "action_plan": "<p>Review March ticket outcomes, confirm service wins, and prepare renewal positioning.</p>",
        },
        {
            "partner_name": "[DEMO] PT Nusantara Retail",
            "name": "[DEMO] Retail Branch Renewal Recovery Playbook",
            "playbook_type": "renewal_readiness",
            "health_state": "at_risk",
            "next_action_date": date(2026, 3, 30),
            "success_goal": "Reduce escalation pressure before renewal confirmation.",
            "risk_note": "Recurring POS issues and pending branch coordination keep the account exposed.",
            "action_plan": "<p>Close known POS findings, confirm onsite outcomes, and schedule renewal follow-up with operations leadership.</p>",
        },
    ]

    for spec in demo_specs:
        partner = partner_model.search([("name", "=", spec["partner_name"])], limit=1)
        if not partner:
            continue
        contract = contract_model.search([("partner_id", "=", (partner.commercial_partner_id or partner).id)], limit=1)
        vals = {
            "partner_id": (partner.commercial_partner_id or partner).id,
            "contract_id": contract.id or False,
            "owner_id": env.user.id,
            "state": "active",
            **{k: v for k, v in spec.items() if k != "partner_name"},
        }
        existing = playbook_model.search([("name", "=", spec["name"])], limit=1)
        if existing:
            existing.write(vals)
            existing._cron_schedule_due_playbooks()
        else:
            playbook = playbook_model.create(vals)
            playbook._cron_schedule_due_playbooks()

    env.cr.commit()

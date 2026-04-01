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

    target_model = env["helpdesk.renewal.target"]
    team = env["helpdesk.ticket.team"].search([("name", "=", "[DEMO] Customer Support")], limit=1)

    demo_targets = [
        {
            "name": "[DEMO] March 2026 Renewal Target",
            "month_start": date(2026, 3, 1),
            "scope_type": "overall",
            "target_amount": 30000000.0,
            "budget_amount": 28000000.0,
            "company_id": env.company.id,
        },
        {
            "name": "[DEMO] April 2026 Renewal Target",
            "month_start": date(2026, 4, 1),
            "scope_type": "overall",
            "target_amount": 34000000.0,
            "budget_amount": 32000000.0,
            "company_id": env.company.id,
        },
    ]
    if team:
        demo_targets.append(
            {
                "name": "[DEMO] March 2026 Support Team Target",
                "month_start": date(2026, 3, 1),
                "scope_type": "team",
                "team_id": team.id,
                "target_amount": 26000000.0,
                "budget_amount": 24000000.0,
                "company_id": env.company.id,
            }
        )

    for vals in demo_targets:
        existing = target_model.search(
            [
                ("name", "=", vals["name"]),
                ("month_start", "=", vals["month_start"]),
                ("scope_type", "=", vals["scope_type"]),
            ],
            limit=1,
        )
        if existing:
            existing.write(vals)
        else:
            target_model.create(vals)

    env.cr.commit()

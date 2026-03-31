from datetime import date, timedelta

from odoo import SUPERUSER_ID, api, fields


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

    renewal_model = env["helpdesk.contract.renewal"]
    handoff_model = env["helpdesk.sales.handoff"]

    contracts = {
        contract.name: contract
        for contract in env["helpdesk.support.contract"].search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] Gold Retainer March 2026",
                        "[DEMO] Branch Operations Support Pack",
                        "[DEMO] Legacy Support Contract 2025",
                    ],
                )
            ]
        )
    }

    demo_rows = [
        {
            "contract_name": "[DEMO] Gold Retainer March 2026",
            "name": "[DEMO] Gold Retainer Renewal Watch",
            "state": "in_review",
            "trigger_type": "low_hours",
            "renewal_probability": 80,
            "expected_revenue": 18000000.0,
            "next_follow_up_date": fields.Date.to_string(date(2026, 3, 31)),
            "commercial_note": (
                "<p>Customer is actively using support hours and should be approached "
                "for a monthly retainer renewal before the remaining balance runs out.</p>"
            ),
        },
        {
            "contract_name": "[DEMO] Branch Operations Support Pack",
            "name": "[DEMO] Branch Support Pack Renewal Watch",
            "state": "open",
            "trigger_type": "expiry",
            "renewal_probability": 65,
            "expected_revenue": 12000000.0,
            "next_follow_up_date": fields.Date.to_string(date(2026, 4, 1)),
            "commercial_note": (
                "<p>Contract end date is approaching. Coordinate with branch operations "
                "stakeholders for renewal scope and commercial approval.</p>"
            ),
        },
        {
            "contract_name": "[DEMO] Legacy Support Contract 2025",
            "name": "[DEMO] Legacy Support Contract Recovery Review",
            "state": "lost",
            "trigger_type": "manual",
            "renewal_probability": 15,
            "expected_revenue": 5000000.0,
            "next_follow_up_date": fields.Date.to_string(date(2026, 4, 15)),
            "commercial_note": (
                "<p>Historical contract recorded for lost-renewal analysis and future "
                "commercial recovery planning.</p>"
            ),
        },
    ]

    for row in demo_rows:
        contract = contracts.get(row["contract_name"])
        if not contract:
            continue
        existing = renewal_model.search(
            [("contract_id", "=", contract.id), ("name", "=", row["name"])],
            limit=1,
        )
        if existing:
            renewal = existing
        else:
            renewal = renewal_model.create(
                {
                    "contract_id": contract.id,
                    "name": row["name"],
                    "state": row["state"],
                    "trigger_type": row["trigger_type"],
                    "renewal_probability": row["renewal_probability"],
                    "expected_revenue": row["expected_revenue"],
                    "next_follow_up_date": row["next_follow_up_date"],
                    "commercial_note": row["commercial_note"],
                    "is_auto_generated": row["trigger_type"] != "manual",
                }
            )
        if (
            contract.name == "[DEMO] Gold Retainer March 2026"
            and not renewal.handoff_id
            and contract.ticket_ids
        ):
            latest_ticket = contract._get_latest_support_ticket()
            handoff = handoff_model.search(
                [("source_contract_id", "=", contract.id), ("reason", "=", "renewal")],
                limit=1,
            )
            if not handoff and latest_ticket:
                handoff = handoff_model.create(
                    {
                        "name": "[DEMO] Gold Retainer Renewal Commercial Review",
                        "ticket_id": latest_ticket.id,
                        "source_contract_id": contract.id,
                        "reason": "renewal",
                        "urgency": "high",
                        "expected_revenue": 18000000.0,
                        "note": (
                            "<p>Support coverage is close to depletion. Please review "
                            "renewal terms and propose the next retainer package.</p>"
                        ),
                        "state": "approved",
                    }
                )
            if handoff:
                renewal.write({"handoff_id": handoff.id, "state": "handoff_sent"})

    env["helpdesk.contract.renewal"].cron_sync_contract_renewals()
    env.cr.commit()

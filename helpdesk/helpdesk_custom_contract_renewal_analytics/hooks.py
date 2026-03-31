from datetime import date

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
    today = date(2026, 3, 31)

    demo_updates = {
        "[DEMO] Gold Retainer Renewal Watch": {
            "state": "handoff_sent",
            "next_follow_up_date": fields.Date.to_string(date(2026, 3, 25)),
            "renewal_probability": 82,
            "expected_revenue": 18500000.0,
            "decision_note": "Commercial review already handed to sales. Follow-up is intentionally overdue for demo analytics visibility.",
        },
        "[DEMO] Branch Support Pack Renewal Watch": {
            "state": "open",
            "next_follow_up_date": fields.Date.to_string(today),
            "renewal_probability": 68,
            "expected_revenue": 12500000.0,
            "decision_note": "Needs branch stakeholder confirmation before formal renewal quote.",
        },
        "[DEMO] Legacy Support Contract Recovery Review": {
            "state": "lost",
            "next_follow_up_date": fields.Date.to_string(date(2026, 4, 15)),
            "renewal_probability": 10,
            "expected_revenue": 5000000.0,
            "decision_note": "Captured as historical lost-renewal data for recovery analysis.",
        },
    }

    for renewal in renewal_model.search([("name", "in", list(demo_updates.keys()))]):
        renewal.write(demo_updates[renewal.name])

    env.cr.commit()

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

    distribution_model = env["helpdesk.service.review.distribution"]
    partner_model = env["res.partner"]

    partner = partner_model.search([("name", "=", "[DEMO] PT Arunika Logistik")], limit=1)
    contact = partner_model.search([("email", "=", "bimo.portal.demo@example.com")], limit=1)
    if partner:
        vals = {
            "name": "[DEMO] Monthly Service Review Delivery",
            "partner_id": (partner.commercial_partner_id or partner).id,
            "recipient_ids": [(6, 0, contact.ids)] if contact else False,
            "owner_id": env.user.id,
            "schedule_type": "monthly",
            "period_mode": "current_month",
            "next_run_date": date(2026, 3, 31),
            "active": True,
        }
        existing = distribution_model.search([("name", "=", vals["name"])], limit=1)
        if existing:
            existing.write(vals)
        else:
            distribution = distribution_model.create(vals)
            distribution.action_run_now()

    env.cr.commit()

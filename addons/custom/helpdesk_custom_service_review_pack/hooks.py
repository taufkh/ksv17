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

    partner_model = env["res.partner"]
    pack_model = env["helpdesk.service.review.pack"]
    date_from = fields.Date.from_string("2026-03-01")
    date_to = fields.Date.from_string("2026-03-31")

    demo_partners = partner_model.search(
        [("name", "in", ["[DEMO] PT Arunika Logistik", "[DEMO] PT Nusantara Retail"])]
    )
    for partner in demo_partners:
        existing = pack_model.search(
            [
                ("partner_id", "=", partner.id),
                ("date_from", "=", date_from),
                ("date_to", "=", date_to),
            ],
            limit=1,
        )
        if existing:
            existing.action_generate_snapshot()
            continue
        pack = pack_model.create(
            {
                "partner_id": partner.id,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        pack.action_generate_snapshot()

    env.cr.commit()

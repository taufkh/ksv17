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

    page_model = env["document.page"]
    contract_model = env["helpdesk.support.contract"]
    partner_model = env["res.partner"]

    articles = {
        page.name: page
        for page in page_model.search(
            [
                (
                    "name",
                    "in",
                    [
                        "[DEMO] Branch manager portal access checklist",
                        "[DEMO] Invoice posting blocked after March patch",
                        "[DEMO] POS sync diagnostic checklist",
                    ],
                )
            ]
        )
    }
    bimo_partner = partner_model.search(
        [("name", "=", "[DEMO] PT Arunika Logistik")], limit=1
    )
    rina_partner = partner_model.search(
        [("name", "=", "[DEMO] PT Nusantara Retail")], limit=1
    )
    gold_contract = contract_model.search(
        [("name", "=", "[DEMO] Gold Retainer March 2026")], limit=1
    )
    branch_contract = contract_model.search(
        [("name", "=", "[DEMO] Branch Operations Support Pack")], limit=1
    )

    configs = [
        (
            "[DEMO] Branch manager portal access checklist",
            {
                "portal_publication_state": "published",
                "portal_visibility": "selected_customers",
                "portal_partner_ids": [(6, 0, [rina_partner.id] if rina_partner else [])],
                "portal_summary": "Checklist for branch manager portal onboarding and secure access activation.",
                "portal_keywords": "portal access onboarding branch manager login",
            },
        ),
        (
            "[DEMO] Invoice posting blocked after March patch",
            {
                "portal_publication_state": "published",
                "portal_visibility": "contract_customers",
                "portal_contract_ids": [(6, 0, [gold_contract.id] if gold_contract else [])],
                "portal_summary": "Troubleshooting guide for invoice posting validation errors after the March patch.",
                "portal_keywords": "invoice posting validation finance patch",
            },
        ),
        (
            "[DEMO] POS sync diagnostic checklist",
            {
                "portal_publication_state": "approved",
                "portal_visibility": "contract_customers",
                "portal_contract_ids": [(6, 0, [branch_contract.id] if branch_contract else [])],
                "portal_summary": "Field checklist for POS sync diagnostics and offline-safe mitigation steps.",
                "portal_keywords": "pos sync checklist branch offline queue",
            },
        ),
    ]

    for name, values in configs:
        article = articles.get(name)
        if not article:
            continue
        values.update(
            {
                "is_helpdesk_article": True,
                "article_status": "portal_ready",
            }
        )
        article.write(values)
        if values["portal_publication_state"] == "published":
            article.write(
                {
                    "portal_published_on": fields.Datetime.now(),
                    "portal_published_by_id": env.user.id,
                }
            )
        elif values["portal_publication_state"] == "approved":
            article.write(
                {
                    "portal_reviewed_on": fields.Datetime.now(),
                    "portal_reviewed_by_id": env.user.id,
                    "portal_approved_on": fields.Datetime.now(),
                    "portal_approved_by_id": env.user.id,
                }
            )

    env.cr.commit()

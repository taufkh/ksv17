from odoo import SUPERUSER_ID, api


def _get_or_create(model, domain, vals):
    record = model.search(domain, limit=1)
    if record:
        record.write(vals)
        return record
    return model.create(vals)


def _ensure_demo_account(env, code, name, account_type, reconcile=False):
    return _get_or_create(
        env["account.account"],
        [
            ("company_id", "=", env.company.id),
            ("code", "=", code),
        ],
        {
            "code": code,
            "name": name,
            "account_type": account_type,
            "company_id": env.company.id,
            "reconcile": reconcile,
        },
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

    company = env.company
    service_categ = env["product.category"].search([], limit=1)
    income_account = env["account.account"].search(
        [("company_id", "=", company.id), ("account_type", "=", "income")], limit=1
    ) or _ensure_demo_account(
        env, "410000", "[DEMO] Helpdesk Revenue", "income", reconcile=False
    )
    receivable_account = env["account.account"].search(
        [("company_id", "=", company.id), ("account_type", "=", "asset_receivable")],
        limit=1,
    ) or _ensure_demo_account(
        env, "110000", "[DEMO] Trade Receivables", "asset_receivable", reconcile=True
    )
    payable_account = env["account.account"].search(
        [("company_id", "=", company.id), ("account_type", "=", "liability_payable")],
        limit=1,
    ) or _ensure_demo_account(
        env, "210000", "[DEMO] Trade Payables", "liability_payable", reconcile=True
    )
    sale_journal = env["account.journal"].search(
        [("type", "=", "sale"), ("company_id", "=", company.id)],
        limit=1,
    )
    if not sale_journal:
        env["account.journal"].create(
            {
                "name": "[DEMO] Helpdesk Sales Journal",
                "code": "HINV",
                "type": "sale",
                "company_id": company.id,
            }
        )

    analysis_product = _get_or_create(
        env["product.product"],
        [("default_code", "=", "HDSK-ANL")],
        {
            "name": "[DEMO] Helpdesk Analysis Hour",
            "default_code": "HDSK-ANL",
            "detailed_type": "service",
            "list_price": 450000.0,
            "categ_id": service_categ.id,
            "property_account_income_id": income_account.id if income_account else False,
        },
    )
    fix_product = _get_or_create(
        env["product.product"],
        [("default_code", "=", "HDSK-FIX")],
        {
            "name": "[DEMO] Helpdesk Bug Fix Hour",
            "default_code": "HDSK-FIX",
            "detailed_type": "service",
            "list_price": 550000.0,
            "categ_id": service_categ.id,
            "property_account_income_id": income_account.id if income_account else False,
        },
    )
    comms_product = _get_or_create(
        env["product.product"],
        [("default_code", "=", "HDSK-COM")],
        {
            "name": "[DEMO] Helpdesk Communication Hour",
            "default_code": "HDSK-COM",
            "detailed_type": "service",
            "list_price": 250000.0,
            "categ_id": service_categ.id,
            "property_account_income_id": income_account.id if income_account else False,
        },
    )

    mapping = {
        "[DEMO] Analysis": analysis_product,
        "[DEMO] Bug Fix": fix_product,
        "[DEMO] Customer Communication": comms_product,
    }
    for name, product in mapping.items():
        time_type = env["project.time.type"].search([("name", "=", name)], limit=1)
        if time_type:
            time_type.write(
                {
                    "invoice_product_id": product.id,
                    "invoice_label": time_type.name,
                }
            )

    teams = env["helpdesk.ticket.team"].search(
        [("name", "in", ["[DEMO] Customer Support", "[DEMO] Billing Desk"])]
    )
    teams.write(
        {
            "allow_billing": True,
            "default_invoice_product_id": analysis_product.id,
            "invoice_grouping": "time_type",
        }
    )

    demo_partners = env["res.partner"].search(
        [
            ("email", "in", [
                "demo.nusantara@example.com",
                "demo.arunika@example.com",
                "rina.portal.demo@example.com",
                "bimo.portal.demo@example.com",
            ])
        ]
    )
    demo_partners.write(
        {
            "property_account_receivable_id": receivable_account.id,
            "property_account_payable_id": payable_account.id,
        }
    )
    company.partner_id.write(
        {
            "property_account_receivable_id": receivable_account.id,
            "property_account_payable_id": payable_account.id,
        }
    )

    ticket = env["helpdesk.ticket"].search([("number", "=", "HT00001")], limit=1)
    if ticket and income_account and receivable_account and not ticket.invoice_count:
        lines = ticket._get_billable_timesheets(uninvoiced_only=True)
        if lines:
            ticket._create_invoice_from_timesheets(lines, grouping="time_type")

    env.cr.commit()

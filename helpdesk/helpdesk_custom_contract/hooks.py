from odoo import SUPERUSER_ID, api, fields


def _get_or_create_contract(env, values):
    contract = env["helpdesk.support.contract"].search(
        [("name", "=", values["name"])],
        limit=1,
    )
    if contract:
        contract.write(values)
        return contract
    return env["helpdesk.support.contract"].create(values)


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

    team = env["helpdesk.ticket.team"].search(
        [("name", "=", "[DEMO] Customer Support")],
        limit=1,
    )

    today = fields.Date.today()
    period_start = today.replace(day=1)
    period_end = fields.Date.end_of(today, "month")

    bimo_partner = env["res.partner"].search(
        [("name", "=", "[DEMO] PT Arunika Logistik")],
        limit=1,
    )
    rina_partner = env["res.partner"].search(
        [("name", "=", "[DEMO] PT Nusantara Retail")],
        limit=1,
    )

    gold_contract = False
    if bimo_partner:
        gold_contract = _get_or_create_contract(
            env,
            {
                "name": "[DEMO] Gold Retainer March 2026",
                "partner_id": bimo_partner.id,
                "team_id": team.id,
                "contract_type": "retainer",
                "sla_tier": "premium",
                "manual_state": "active",
                "start_date": period_start,
                "end_date": period_end,
                "included_hours": 12.0,
                "warning_hours": 3.0,
                "allow_overrun": True,
                "notes": "<p>Monthly gold support retainer covering accounting and billing incidents.</p>",
            },
        )

    branch_contract = False
    if rina_partner:
        branch_contract = _get_or_create_contract(
            env,
            {
                "name": "[DEMO] Branch Operations Support Pack",
                "partner_id": rina_partner.id,
                "team_id": team.id,
                "contract_type": "block",
                "sla_tier": "standard",
                "manual_state": "active",
                "start_date": period_start,
                "end_date": period_end,
                "included_hours": 8.0,
                "warning_hours": 2.0,
                "allow_overrun": False,
                "notes": "<p>Support pack for portal access, branch onboarding, and operational support questions.</p>",
            },
        )
        _get_or_create_contract(
            env,
            {
                "name": "[DEMO] Legacy Support Contract 2025",
                "partner_id": rina_partner.id,
                "team_id": team.id,
                "contract_type": "retainer",
                "sla_tier": "standard",
                "manual_state": "active",
                "start_date": fields.Date.from_string("2025-01-01"),
                "end_date": fields.Date.from_string("2025-12-31"),
                "included_hours": 20.0,
                "warning_hours": 4.0,
                "allow_overrun": True,
                "notes": "<p>Previous annual contract kept as historical reference.</p>",
            },
        )

    if gold_contract:
        env["helpdesk.ticket"].search(
            [("name", "in", [
                "[DEMO] Cannot post invoice to customer",
                "[DEMO] Quarterly support retainer question",
            ])]
        ).write({"support_contract_id": gold_contract.id})

    if branch_contract:
        env["helpdesk.ticket"].search(
            [("name", "in", [
                "[DEMO] Need new portal access for branch manager",
                "[DEMO] Legacy ticket awaiting customer reply",
            ])]
        ).write({"support_contract_id": branch_contract.id})

    env["helpdesk.ticket"].search([("name", "=", "[DEMO] POS sync error after patch")], limit=1).write(
        {"support_contract_id": False}
    )

    env.cr.commit()


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

    converted_ticket = env["helpdesk.ticket"].search(
        [("name", "=", "[DEMO] CRM lead follow-up from support case")],
        limit=1,
    )
    converted_lead = env["crm.lead"].search(
        [("name", "=", "[DEMO] Implementation workshop upsell")],
        limit=1,
    )
    if converted_ticket and converted_lead and not env["helpdesk.sales.handoff"].search(
        [("ticket_id", "=", converted_ticket.id), ("lead_id", "=", converted_lead.id)],
        limit=1,
    ):
        env["helpdesk.sales.handoff"].create(
            {
                "name": "[DEMO] Workshop upsell handoff",
                "ticket_id": converted_ticket.id,
                "reason": "upsell",
                "urgency": "high",
                "sales_team_id": converted_lead.team_id.id,
                "sales_user_id": converted_lead.user_id.id,
                "expected_revenue": 35000000,
                "note": "<p>Customer requested an implementation workshop after the support issue was resolved.</p>",
                "state": "converted",
                "lead_id": converted_lead.id,
            }
        )

    requested_ticket = env["helpdesk.ticket"].search(
        [("name", "=", "[DEMO] Quarterly support retainer question")],
        limit=1,
    )
    if requested_ticket and not env["helpdesk.sales.handoff"].search(
        [("ticket_id", "=", requested_ticket.id), ("state", "=", "requested")],
        limit=1,
    ):
        env["helpdesk.sales.handoff"].create(
            {
                "name": "[DEMO] Retainer renewal follow-up",
                "ticket_id": requested_ticket.id,
                "reason": "renewal",
                "urgency": "normal",
                "expected_revenue": 18000000,
                "note": "<p>Customer is asking for quarterly retainer pricing and expects a formal quote.</p>",
                "state": "requested",
            }
        )

    env.cr.commit()

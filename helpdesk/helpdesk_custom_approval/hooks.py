from odoo import SUPERUSER_ID, api, fields


def _get_or_create_approval(env, values):
    approval = env["helpdesk.ticket.approval"].search(
        [("ticket_id", "=", values["ticket_id"]), ("name", "=", values["name"])],
        limit=1,
    )
    if approval:
        approval.write(values)
        return approval
    return env["helpdesk.ticket.approval"].create(values)


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

    admin_user = env.ref("base.user_admin")
    demo_support = env["res.users"].search(
        [("login", "=", "support.demo@example.com")],
        limit=1,
    )

    def ticket_by_name(name):
        return env["helpdesk.ticket"].search([("name", "=", name)], limit=1)

    pending_ticket = ticket_by_name("[DEMO] Cannot post invoice to customer")
    if pending_ticket:
        _get_or_create_approval(
            env,
            {
                "name": "[DEMO] Billing exception approval",
                "ticket_id": pending_ticket.id,
                "approval_type": "billing_exception",
                "urgency": "high",
                "approver_id": admin_user.id,
                "requested_amount": 1250000,
                "required_by_date": fields.Date.today(),
                "justification": (
                    "<p>Customer requests invoice correction and fee waiver because "
                    "the March patch blocked posting.</p>"
                ),
                "customer_impact": (
                    "<p>Month-end billing is blocked and finance cannot complete reconciliation.</p>"
                ),
                "state": "requested",
            },
        )

    review_ticket = ticket_by_name("[DEMO] CRM lead follow-up from support case")
    if review_ticket:
        _get_or_create_approval(
            env,
            {
                "name": "[DEMO] Onsite visit approval",
                "ticket_id": review_ticket.id,
                "approval_type": "onsite_visit",
                "urgency": "normal",
                "approver_id": admin_user.id,
                "required_by_date": fields.Date.today(),
                "justification": (
                    "<p>Support proposes a branch visit to validate the workflow "
                    "and confirm the issue scope with the customer.</p>"
                ),
                "customer_impact": (
                    "<p>Customer follow-up is delayed without direct validation from the support team.</p>"
                ),
                "state": "in_review",
                "review_date": fields.Datetime.now(),
            },
        )

    approved_ticket = ticket_by_name("[DEMO] POS sync error after patch")
    if approved_ticket:
        _get_or_create_approval(
            env,
            {
                "name": "[DEMO] Replacement unit approval",
                "ticket_id": approved_ticket.id,
                "approval_type": "replacement",
                "urgency": "urgent",
                "approver_id": admin_user.id,
                "required_by_date": fields.Date.today(),
                "justification": (
                    "<p>Store operations require a temporary replacement device while "
                    "the sync issue is being fixed.</p>"
                ),
                "customer_impact": (
                    "<p>Checkout transactions are disrupted during peak trading hours.</p>"
                ),
                "state": "approved",
                "review_date": fields.Datetime.now(),
                "decision_date": fields.Datetime.now(),
                "decision_by_id": admin_user.id,
                "decision_note": "Approved for immediate replacement dispatch.",
            },
        )

    rejected_ticket = ticket_by_name("[DEMO] Legacy ticket awaiting customer reply")
    if rejected_ticket:
        _get_or_create_approval(
            env,
            {
                "name": "[DEMO] SLA waiver request",
                "ticket_id": rejected_ticket.id,
                "approval_type": "sla_waiver",
                "urgency": "low",
                "approver_id": demo_support.id or admin_user.id,
                "required_by_date": fields.Date.today(),
                "justification": (
                    "<p>Agent requested an SLA waiver because the customer has not replied for several days.</p>"
                ),
                "customer_impact": (
                    "<p>No direct operational impact at the moment because the customer response is pending.</p>"
                ),
                "state": "rejected",
                "review_date": fields.Datetime.now(),
                "decision_date": fields.Datetime.now(),
                "decision_by_id": admin_user.id,
                "decision_note": "Rejected. Existing inactive close policy is sufficient.",
            },
        )

    implemented_ticket = ticket_by_name("[DEMO] Need new portal access for branch manager")
    if implemented_ticket:
        _get_or_create_approval(
            env,
            {
                "name": "[DEMO] Access exception approval",
                "ticket_id": implemented_ticket.id,
                "approval_type": "access_exception",
                "urgency": "normal",
                "approver_id": admin_user.id,
                "required_by_date": fields.Date.today(),
                "justification": (
                    "<p>Temporary elevated access was requested so the branch manager "
                    "could validate approval routing before go-live.</p>"
                ),
                "customer_impact": (
                    "<p>Go-live readiness would be delayed if the branch manager cannot validate the flow.</p>"
                ),
                "state": "implemented",
                "review_date": fields.Datetime.now(),
                "decision_date": fields.Datetime.now(),
                "implemented_date": fields.Datetime.now(),
                "decision_by_id": admin_user.id,
                "implemented_by_id": demo_support.id or admin_user.id,
                "decision_note": "Approved and executed during branch onboarding support.",
            },
        )

    env.cr.commit()


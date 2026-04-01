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

    env["ir.config_parameter"].sudo().set_param(
        "helpdesk_custom_whatsapp.enabled", "True"
    )
    env["ir.config_parameter"].sudo().set_param(
        "helpdesk_custom_whatsapp.sandbox_mode", "True"
    )

    partner_updates = {
        "support.demo@example.com": "+6281111110099",
        "rina.portal.demo@example.com": "+6281111110001",
        "bimo.portal.demo@example.com": "+6281111110002",
        "admin@example.com": "+6281111110000",
    }
    for email, mobile in partner_updates.items():
        partner = env["res.partner"].search([("email", "=", email)], limit=1)
        if partner and not partner.mobile:
            partner.mobile = mobile

    admin_partner = env.ref("base.user_admin").partner_id
    if admin_partner and not admin_partner.mobile:
        admin_partner.mobile = "+6281111110000"

    ticket_model = env["helpdesk.ticket"].with_context(skip_helpdesk_whatsapp=True)

    ticket_stage = ticket_model.search([("number", "=", "HT00001")], limit=1)
    if ticket_stage:
        ticket_stage._queue_whatsapp_notifications(
            "stage_update",
            extra_context={
                "previous_stage_name": "Awaiting",
                "changed_by_name": env.user.name,
            },
        )

    ticket_escalation = ticket_model.search([("number", "=", "HT00003")], limit=1)
    if ticket_escalation:
        escalation_event = ticket_escalation.escalation_event_ids.sorted("id")[-1:]
        if escalation_event:
            ticket_escalation._queue_whatsapp_notifications(
                "escalation", event=escalation_event
            )

    ticket_closed = ticket_model.search([("number", "=", "HT00007")], limit=1)
    if ticket_closed:
        ticket_closed._queue_whatsapp_notifications(
            "ticket_closed",
            extra_context={"changed_by_name": env.user.name},
        )

    env["helpdesk.whatsapp.message"].sudo()._cron_process_queue(limit=100)
    env.cr.commit()

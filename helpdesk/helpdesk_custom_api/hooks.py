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
    params = env["ir.config_parameter"].sudo()
    if not params.get_param("helpdesk_custom_api.enabled"):
        params.set_param("helpdesk_custom_api.enabled", "True")
    if not params.get_param("helpdesk_custom_api.token"):
        params.set_param("helpdesk_custom_api.token", "ksv17-demo-api-token")
    if not params.get_param("helpdesk_custom_api.allow_attachment_upload"):
        params.set_param("helpdesk_custom_api.allow_attachment_upload", "True")
    if not params.get_param("helpdesk_custom_api.max_attachment_mb"):
        params.set_param("helpdesk_custom_api.max_attachment_mb", "10")
    if not params.get_param("helpdesk_custom_api.default_team_id"):
        demo_team = env["helpdesk.ticket.team"].search(
            [("name", "=", "[DEMO] Customer Support")], limit=1
        )
        if demo_team:
            params.set_param("helpdesk_custom_api.default_team_id", str(demo_team.id))
    env.cr.commit()

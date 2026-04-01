{
    "name": "Helpdesk Custom Customer Success Playbook",
    "version": "17.0.1.0.0",
    "summary": "Customer success playbooks and proactive renewal tasks",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": [
        "helpdesk_feature_hub",
        "helpdesk_custom_contract_renewal_analytics",
        "helpdesk_custom_customer_360",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron_data.xml",
        "views/helpdesk_customer_success_playbook_views.xml",
        "views/res_partner_views.xml",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
}

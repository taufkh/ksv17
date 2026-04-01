import base64
from datetime import timedelta

from odoo import SUPERUSER_ID, Command, api, fields


MODULE_FLAG = "helpdesk_custom_demo.sample_data_ready"
DEMO_PASSWORD = "demo123"


def _get_or_create(model, domain, vals):
    record = model.search(domain, limit=1)
    if record:
        record.write(vals)
        return record
    return model.create(vals)


def _set_ticket_dates(
    env,
    ticket,
    *,
    create_dt,
    assigned_dt=None,
    last_stage_dt=None,
    closed_dt=None,
    sla_deadline=None,
):
    env.cr.execute(
        """
        UPDATE helpdesk_ticket
           SET create_date = %s,
               write_date = %s,
               assigned_date = %s,
               last_stage_update = %s,
               closed_date = %s
               ,sla_deadline = %s
         WHERE id = %s
        """,
        (
            create_dt,
            create_dt,
            assigned_dt,
            last_stage_dt or create_dt,
            closed_dt,
            sla_deadline,
            ticket.id,
        ),
    )


def post_init_hook(env):
    env = api.Environment(
        env.cr,
        SUPERUSER_ID,
        {
            "tracking_disable": True,
            "mail_create_nosubscribe": True,
            "mail_notrack": True,
            "no_reset_password": True,
        },
    )
    if env["ir.config_parameter"].sudo().get_param(MODULE_FLAG):
        return

    company = env.company
    admin_user = env.ref("base.user_admin")
    admin_partner = admin_user.partner_id
    portal_group = env.ref("base.group_portal")
    internal_group = env.ref("base.group_user")
    helpdesk_user_group = env.ref("helpdesk_mgmt.group_helpdesk_user")
    alias_model = env.ref("helpdesk_mgmt.model_helpdesk_ticket")
    new_stage = env.ref("helpdesk_mgmt.helpdesk_ticket_stage_new")
    progress_stage = env.ref("helpdesk_mgmt.helpdesk_ticket_stage_in_progress")
    awaiting_stage = env.ref("helpdesk_mgmt.helpdesk_ticket_stage_awaiting")
    done_stage = env.ref("helpdesk_mgmt.helpdesk_ticket_stage_done")
    cancelled_stage = env.ref("helpdesk_mgmt.helpdesk_ticket_stage_cancelled")
    rating_template = env.ref("helpdesk_mgmt_rating.rating_ticket_email_template")
    web_channel = env.ref("helpdesk_mgmt.helpdesk_ticket_channel_web")
    email_channel = env.ref("helpdesk_mgmt.helpdesk_ticket_channel_email")
    phone_channel = env.ref("helpdesk_mgmt.helpdesk_ticket_channel_phone")
    pricelist = env["product.pricelist"].search([("company_id", "in", [False, company.id])], limit=1)
    if not pricelist:
        pricelist = env["product.pricelist"].create(
            {
                "name": "[DEMO] Default Pricelist",
                "currency_id": company.currency_id.id,
                "company_id": company.id,
            }
        )

    company.write(
        {
            "helpdesk_mgmt_portal_select_team": True,
            "helpdesk_mgmt_portal_team_id_required": True,
            "helpdesk_mgmt_portal_category_id_required": True,
            "helpdesk_mgmt_portal_type": True,
            "helpdesk_mgmt_portal_type_id_required": True,
        }
    )

    required_fields = env["ir.model.fields"].search(
        [
            ("model", "=", "helpdesk.ticket"),
            ("name", "in", ["partner_id", "category_id", "type_id"]),
        ]
    )
    done_stage.write(
        {
            "rating_mail_template_id": rating_template.id,
            "validate_field_ids": [Command.set(required_fields.ids)],
        }
    )

    bug_type = _get_or_create(
        env["helpdesk.ticket.type"],
        [("name", "=", "[DEMO] Bug")],
        {"name": "[DEMO] Bug", "show_in_portal": True},
    )
    service_type = _get_or_create(
        env["helpdesk.ticket.type"],
        [("name", "=", "[DEMO] Service Request")],
        {"name": "[DEMO] Service Request", "show_in_portal": True},
    )
    change_type = _get_or_create(
        env["helpdesk.ticket.type"],
        [("name", "=", "[DEMO] Change Request")],
        {"name": "[DEMO] Change Request", "show_in_portal": True},
    )

    functional_category = _get_or_create(
        env["helpdesk.ticket.category"],
        [("name", "=", "[DEMO] Functional Issue")],
        {
            "name": "[DEMO] Functional Issue",
            "company_id": company.id,
            "show_in_portal": True,
            "template_description": (
                "<p>Describe the workflow, exact menu, and error message."
                " Include steps to reproduce and expected result.</p>"
            ),
        },
    )
    access_category = _get_or_create(
        env["helpdesk.ticket.category"],
        [("name", "=", "[DEMO] Access Request")],
        {
            "name": "[DEMO] Access Request",
            "company_id": company.id,
            "show_in_portal": True,
            "template_description": (
                "<p>Specify user name, branch, requested role, and required access date.</p>"
            ),
        },
    )
    billing_category = _get_or_create(
        env["helpdesk.ticket.category"],
        [("name", "=", "[DEMO] Billing Query")],
        {
            "name": "[DEMO] Billing Query",
            "company_id": company.id,
            "show_in_portal": True,
            "template_description": (
                "<p>Provide invoice number, customer name, disputed amount, and issue summary.</p>"
            ),
        },
    )

    vip_tag = _get_or_create(
        env["helpdesk.ticket.tag"],
        [("name", "=", "[DEMO] VIP")],
        {"name": "[DEMO] VIP", "color": 1, "company_id": company.id},
    )
    integration_tag = _get_or_create(
        env["helpdesk.ticket.tag"],
        [("name", "=", "[DEMO] Integration")],
        {"name": "[DEMO] Integration", "color": 2, "company_id": company.id},
    )
    invoice_tag = _get_or_create(
        env["helpdesk.ticket.tag"],
        [("name", "=", "[DEMO] Invoice")],
        {"name": "[DEMO] Invoice", "color": 3, "company_id": company.id},
    )

    analysis_type = _get_or_create(
        env["project.time.type"],
        [("name", "=", "[DEMO] Analysis")],
        {"name": "[DEMO] Analysis", "code": "ANL"},
    )
    bugfix_type = _get_or_create(
        env["project.time.type"],
        [("name", "=", "[DEMO] Bug Fix")],
        {"name": "[DEMO] Bug Fix", "code": "FIX"},
    )
    comms_type = _get_or_create(
        env["project.time.type"],
        [("name", "=", "[DEMO] Customer Communication")],
        {"name": "[DEMO] Customer Communication", "code": "COM"},
    )

    project = _get_or_create(
        env["project.project"],
        [("name", "=", "[DEMO] Helpdesk Delivery")],
        {
            "name": "[DEMO] Helpdesk Delivery",
            "company_id": company.id,
            "allow_timesheets": True,
        },
    )
    task = _get_or_create(
        env["project.task"],
        [("name", "=", "[DEMO] Customer Onboarding Fixes"), ("project_id", "=", project.id)],
        {
            "name": "[DEMO] Customer Onboarding Fixes",
            "project_id": project.id,
            "company_id": company.id,
        },
    )

    support_alias = _get_or_create(
        env["mail.alias"],
        [("alias_name", "=", "demo.support")],
        {
            "alias_name": "demo.support",
            "alias_model_id": alias_model.id,
            "alias_contact": "everyone",
        },
    )
    billing_alias = _get_or_create(
        env["mail.alias"],
        [("alias_name", "=", "demo.billing")],
        {
            "alias_name": "demo.billing",
            "alias_model_id": alias_model.id,
            "alias_contact": "everyone",
        },
    )

    support_team = _get_or_create(
        env["helpdesk.ticket.team"],
        [("name", "=", "[DEMO] Customer Support")],
        {
            "name": "[DEMO] Customer Support",
            "company_id": company.id,
            "alias_id": support_alias.id,
            "user_id": admin_user.id,
            "user_ids": [Command.set([admin_user.id])],
            "category_ids": [Command.set([functional_category.id, access_category.id, billing_category.id])],
            "type_ids": [Command.set([bug_type.id, service_type.id, change_type.id])],
            "show_in_portal": True,
            "assign_method": "balanced",
            "use_sla": True,
            "resource_calendar_id": company.resource_calendar_id.id,
            "allow_timesheet": True,
            "default_project_id": project.id,
            "close_inactive_tickets": True,
            "ticket_stage_ids": [Command.set([awaiting_stage.id, progress_stage.id])],
            "inactive_tickets_day_limit_warning": 3,
            "inactive_tickets_day_limit_closing": 5,
            "closing_ticket_stage": done_stage.id,
            "autoupdate_ticket_stage": True,
            "autopupdate_src_stage_ids": [Command.set([awaiting_stage.id])],
            "autopupdate_dest_stage_id": progress_stage.id,
        },
    )
    support_alias.write({"alias_defaults": "{'team_id': %d}" % support_team.id})

    billing_team = _get_or_create(
        env["helpdesk.ticket.team"],
        [("name", "=", "[DEMO] Billing Desk")],
        {
            "name": "[DEMO] Billing Desk",
            "company_id": company.id,
            "alias_id": billing_alias.id,
            "user_id": admin_user.id,
            "user_ids": [Command.set([admin_user.id])],
            "category_ids": [Command.set([billing_category.id])],
            "type_ids": [Command.set([service_type.id, change_type.id])],
            "show_in_portal": True,
            "assign_method": "manual",
            "use_sla": True,
            "resource_calendar_id": company.resource_calendar_id.id,
        },
    )
    billing_alias.write({"alias_defaults": "{'team_id': %d}" % billing_team.id})

    admin_partner.write(
        {
            "helpdesk_team_ids": [Command.set([support_team.id, billing_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, access_category.id, billing_category.id])],
        }
    )

    nusantara_company = _get_or_create(
        env["res.partner"],
        [("name", "=", "[DEMO] PT Nusantara Retail"), ("company_type", "=", "company")],
        {
            "name": "[DEMO] PT Nusantara Retail",
            "company_type": "company",
            "email": "demo.nusantara@example.com",
            "phone": "+62-21-555-0101",
            "helpdesk_team_ids": [Command.set([support_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, access_category.id])],
        },
    )
    nusantara_contact = _get_or_create(
        env["res.partner"],
        [("email", "=", "rina.portal.demo@example.com")],
        {
            "name": "[DEMO] Rina Portal",
            "parent_id": nusantara_company.id,
            "email": "rina.portal.demo@example.com",
            "phone": "+62-811-1111-0001",
            "helpdesk_team_ids": [Command.set([support_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, access_category.id])],
        },
    )
    arunika_company = _get_or_create(
        env["res.partner"],
        [("name", "=", "[DEMO] PT Arunika Logistik"), ("company_type", "=", "company")],
        {
            "name": "[DEMO] PT Arunika Logistik",
            "company_type": "company",
            "email": "demo.arunika@example.com",
            "phone": "+62-21-555-0202",
            "helpdesk_team_ids": [Command.set([support_team.id, billing_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, billing_category.id])],
        },
    )
    arunika_contact = _get_or_create(
        env["res.partner"],
        [("email", "=", "bimo.portal.demo@example.com")],
        {
            "name": "[DEMO] Bimo Finance",
            "parent_id": arunika_company.id,
            "email": "bimo.portal.demo@example.com",
            "phone": "+62-811-1111-0002",
            "helpdesk_team_ids": [Command.set([support_team.id, billing_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, billing_category.id])],
        },
    )
    support_partner = _get_or_create(
        env["res.partner"],
        [("email", "=", "support.demo@example.com")],
        {
            "name": "[DEMO] Support Agent",
            "email": "support.demo@example.com",
            "helpdesk_team_ids": [Command.set([support_team.id, billing_team.id])],
            "helpdesk_category_ids": [Command.set([functional_category.id, access_category.id, billing_category.id])],
        },
    )

    support_user = _get_or_create(
        env["res.users"],
        [("login", "=", "support.demo@example.com")],
        {
            "name": "[DEMO] Support Agent",
            "login": "support.demo@example.com",
            "email": "support.demo@example.com",
            "partner_id": support_partner.id,
            "company_id": company.id,
            "company_ids": [Command.set([company.id])],
            "groups_id": [Command.set([internal_group.id, helpdesk_user_group.id])],
            "password": DEMO_PASSWORD,
            "notification_type": "inbox",
        },
    )
    portal_user_1 = _get_or_create(
        env["res.users"],
        [("login", "=", "rina.portal.demo@example.com")],
        {
            "name": "[DEMO] Rina Portal",
            "login": "rina.portal.demo@example.com",
            "email": "rina.portal.demo@example.com",
            "partner_id": nusantara_contact.id,
            "company_id": company.id,
            "company_ids": [Command.set([company.id])],
            "groups_id": [Command.set([portal_group.id])],
            "password": DEMO_PASSWORD,
            "notification_type": "email",
        },
    )
    portal_user_2 = _get_or_create(
        env["res.users"],
        [("login", "=", "bimo.portal.demo@example.com")],
        {
            "name": "[DEMO] Bimo Finance",
            "login": "bimo.portal.demo@example.com",
            "email": "bimo.portal.demo@example.com",
            "partner_id": arunika_contact.id,
            "company_id": company.id,
            "company_ids": [Command.set([company.id])],
            "groups_id": [Command.set([portal_group.id])],
            "password": DEMO_PASSWORD,
            "notification_type": "email",
        },
    )

    support_team.write(
        {
            "user_ids": [Command.set([admin_user.id, support_user.id])],
            "helpdesk_partner_ids": [Command.set([nusantara_company.id, nusantara_contact.id, arunika_company.id, arunika_contact.id])],
        }
    )
    billing_team.write(
        {
            "user_ids": [Command.set([admin_user.id, support_user.id])],
            "helpdesk_partner_ids": [Command.set([arunika_company.id, arunika_contact.id])],
        }
    )
    functional_category.write(
        {"helpdesk_category_partner_ids": [Command.set([nusantara_company.id, nusantara_contact.id, arunika_company.id, arunika_contact.id])]}
    )
    access_category.write(
        {"helpdesk_category_partner_ids": [Command.set([nusantara_company.id, nusantara_contact.id])]}
    )
    billing_category.write(
        {"helpdesk_category_partner_ids": [Command.set([arunika_company.id, arunika_contact.id])]}
    )

    sale_order = _get_or_create(
        env["sale.order"],
        [("client_order_ref", "=", "DEMO-HDSK-001")],
        {
            "partner_id": arunika_company.id,
            "partner_invoice_id": arunika_company.id,
            "partner_shipping_id": arunika_company.id,
            "pricelist_id": pricelist.id,
            "client_order_ref": "DEMO-HDSK-001",
            "company_id": company.id,
        },
    )

    fast_response_sla = _get_or_create(
        env["helpdesk.sla"],
        [("name", "=", "[DEMO] Priority Response 4H")],
        {
            "name": "[DEMO] Priority Response 4H",
            "team_ids": [Command.set([support_team.id])],
            "category_ids": [Command.set([functional_category.id, billing_category.id])],
            "days": 0,
            "hours": 4,
            "stage_ids": [Command.set([done_stage.id, cancelled_stage.id])],
        },
    )
    access_sla = _get_or_create(
        env["helpdesk.sla"],
        [("name", "=", "[DEMO] Access Request 8H")],
        {
            "name": "[DEMO] Access Request 8H",
            "team_ids": [Command.set([support_team.id])],
            "category_ids": [Command.set([access_category.id])],
            "days": 0,
            "hours": 8,
            "stage_ids": [Command.set([done_stage.id, cancelled_stage.id])],
        },
    )
    billing_sla = _get_or_create(
        env["helpdesk.sla"],
        [("name", "=", "[DEMO] Billing Resolution 1D")],
        {
            "name": "[DEMO] Billing Resolution 1D",
            "team_ids": [Command.set([billing_team.id])],
            "category_ids": [Command.set([billing_category.id])],
            "days": 1,
            "hours": 0,
            "stage_ids": [Command.set([done_stage.id, cancelled_stage.id])],
        },
    )
    _ = fast_response_sla, access_sla, billing_sla

    ticket_1 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] Cannot post invoice to customer")],
        {
            "name": "[DEMO] Cannot post invoice to customer",
            "description": "<p>Posting invoice returns a validation error after the March patch.</p>",
            "partner_id": arunika_contact.id,
            "partner_email": arunika_contact.email,
            "team_id": support_team.id,
            "type_id": bug_type.id,
            "category_id": billing_category.id,
            "priority": "3",
            "stage_id": progress_stage.id,
            "channel_id": email_channel.id,
            "tag_ids": [Command.set([vip_tag.id, invoice_tag.id])],
            "project_id": project.id,
            "task_id": task.id,
            "planned_hours": 6.0,
            "sale_order_ids": [Command.set([sale_order.id])],
        },
    )
    ticket_2 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] Need new portal access for branch manager")],
        {
            "name": "[DEMO] Need new portal access for branch manager",
            "description": "<p>Please create portal access for the Surabaya branch manager before Monday.</p>",
            "partner_id": nusantara_contact.id,
            "partner_email": nusantara_contact.email,
            "team_id": support_team.id,
            "type_id": service_type.id,
            "category_id": access_category.id,
            "priority": "1",
            "stage_id": awaiting_stage.id,
            "channel_id": web_channel.id,
        },
    )
    ticket_3 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] POS sync error after patch")],
        {
            "name": "[DEMO] POS sync error after patch",
            "description": "<p>POS transactions stop syncing to accounting after the nightly deployment.</p>",
            "partner_id": nusantara_contact.id,
            "partner_email": nusantara_contact.email,
            "team_id": support_team.id,
            "type_id": bug_type.id,
            "category_id": functional_category.id,
            "priority": "2",
            "stage_id": progress_stage.id,
            "channel_id": phone_channel.id,
            "tag_ids": [Command.set([integration_tag.id])],
            "project_id": project.id,
            "task_id": task.id,
            "planned_hours": 8.0,
        },
    )
    ticket_4 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] POS sync error after patch (duplicate)")],
        {
            "name": "[DEMO] POS sync error after patch (duplicate)",
            "description": "<p>Customer reported the same POS sync issue via another channel.</p>",
            "partner_id": nusantara_contact.id,
            "partner_email": nusantara_contact.email,
            "team_id": support_team.id,
            "type_id": bug_type.id,
            "category_id": functional_category.id,
            "priority": "1",
            "stage_id": new_stage.id,
            "channel_id": email_channel.id,
            "tag_ids": [Command.set([integration_tag.id])],
        },
    )
    ticket_5 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] Quarterly support retainer question")],
        {
            "name": "[DEMO] Quarterly support retainer question",
            "description": "<p>Customer requested clarification on the April retainer invoice.</p>",
            "partner_id": arunika_contact.id,
            "partner_email": arunika_contact.email,
            "team_id": billing_team.id,
            "type_id": service_type.id,
            "category_id": billing_category.id,
            "priority": "0",
            "stage_id": done_stage.id,
            "channel_id": email_channel.id,
            "sale_order_ids": [Command.set([sale_order.id])],
            "user_id": admin_user.id,
        },
    )
    ticket_6 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] CRM lead follow-up from support case")],
        {
            "name": "[DEMO] CRM lead follow-up from support case",
            "description": "<p>Customer asked for an implementation workshop after solving a support case.</p>",
            "partner_id": nusantara_contact.id,
            "partner_email": nusantara_contact.email,
            "team_id": support_team.id,
            "type_id": change_type.id,
            "category_id": functional_category.id,
            "priority": "1",
            "stage_id": progress_stage.id,
            "channel_id": web_channel.id,
            "project_id": project.id,
            "task_id": task.id,
            "user_id": support_user.id,
        },
    )
    ticket_7 = _get_or_create(
        env["helpdesk.ticket"],
        [("name", "=", "[DEMO] Legacy ticket awaiting customer reply")],
        {
            "name": "[DEMO] Legacy ticket awaiting customer reply",
            "description": "<p>No customer reply received for almost a week.</p>",
            "partner_id": nusantara_contact.id,
            "partner_email": nusantara_contact.email,
            "team_id": support_team.id,
            "type_id": service_type.id,
            "category_id": access_category.id,
            "priority": "0",
            "stage_id": awaiting_stage.id,
            "channel_id": email_channel.id,
        },
    )

    ticket_3.write({"related_ticket_ids": [Command.link(ticket_4.id)]})
    ticket_4.write({"related_ticket_ids": [Command.link(ticket_3.id)]})

    lead = _get_or_create(
        env["crm.lead"],
        [("name", "=", "[DEMO] Implementation workshop upsell")],
        {
            "name": "[DEMO] Implementation workshop upsell",
            "partner_id": nusantara_company.id,
            "ticket_id": ticket_6.id,
            "type": "opportunity",
            "user_id": admin_user.id,
        },
    )
    _ = lead

    attachment = _get_or_create(
        env["ir.attachment"],
        [("name", "=", "demo_access_request.txt"), ("res_model", "=", "helpdesk.ticket"), ("res_id", "=", ticket_2.id)],
        {
            "name": "demo_access_request.txt",
            "datas": base64.b64encode(
                b"Requested access:\n- Branch: Surabaya\n- Role: Branch Manager\n- Needed: Monday 09:00 WIB\n"
            ),
            "res_model": "helpdesk.ticket",
            "res_id": ticket_2.id,
            "type": "binary",
            "mimetype": "text/plain",
        },
    )
    _ = attachment

    ticket_1.message_post(body="Demo note: accounting confirmed the bug appears after the latest patch.")
    ticket_2.message_post(body="Demo note: customer uploaded branch approval request.")
    ticket_5.message_post(body="Demo note: ticket solved and customer asked only for invoice clarification.")

    employee = admin_user.employee_id or env["hr.employee"].search([("user_id", "=", admin_user.id)], limit=1)
    if not employee:
        employee = env["hr.employee"].create({"name": admin_user.name, "user_id": admin_user.id})
    today = fields.Date.today()
    env["account.analytic.line"].create(
        [
            {
                "name": "[DEMO] Invoice posting investigation",
                "employee_id": employee.id,
                "user_id": admin_user.id,
                "date": today - timedelta(days=2),
                "unit_amount": 1.5,
                "project_id": project.id,
                "task_id": task.id,
                "ticket_id": ticket_1.id,
                "time_type_id": analysis_type.id,
            },
            {
                "name": "[DEMO] Fix validation rule",
                "employee_id": employee.id,
                "user_id": admin_user.id,
                "date": today - timedelta(days=1),
                "unit_amount": 2.0,
                "project_id": project.id,
                "task_id": task.id,
                "ticket_id": ticket_1.id,
                "time_type_id": bugfix_type.id,
            },
            {
                "name": "[DEMO] Customer status update",
                "employee_id": employee.id,
                "user_id": admin_user.id,
                "date": today - timedelta(days=1),
                "unit_amount": 0.5,
                "project_id": project.id,
                "task_id": task.id,
                "ticket_id": ticket_3.id,
                "time_type_id": comms_type.id,
            },
        ]
    )

    now = fields.Datetime.now()
    _set_ticket_dates(
        env,
        ticket_1,
        create_dt=now - timedelta(days=5),
        assigned_dt=now - timedelta(days=5),
        last_stage_dt=now - timedelta(days=1),
        sla_deadline=now + timedelta(days=1),
    )
    _set_ticket_dates(
        env,
        ticket_2,
        create_dt=now - timedelta(days=4),
        assigned_dt=now - timedelta(days=4),
        last_stage_dt=now - timedelta(days=3),
        sla_deadline=now + timedelta(days=2),
    )
    _set_ticket_dates(
        env,
        ticket_3,
        create_dt=now - timedelta(days=10),
        assigned_dt=now - timedelta(days=10),
        last_stage_dt=now - timedelta(days=3),
        sla_deadline=now - timedelta(days=2),
    )
    _set_ticket_dates(
        env,
        ticket_4,
        create_dt=now - timedelta(days=8),
        assigned_dt=now - timedelta(days=8),
        last_stage_dt=now - timedelta(days=7),
        sla_deadline=now + timedelta(days=1),
    )
    _set_ticket_dates(
        env,
        ticket_5,
        create_dt=now - timedelta(days=12),
        assigned_dt=now - timedelta(days=12),
        last_stage_dt=now - timedelta(days=9),
        closed_dt=now - timedelta(days=9),
        sla_deadline=now - timedelta(days=8),
    )
    _set_ticket_dates(
        env,
        ticket_6,
        create_dt=now - timedelta(days=3),
        assigned_dt=now - timedelta(days=3),
        last_stage_dt=now - timedelta(days=1),
        sla_deadline=now + timedelta(days=2),
    )
    _set_ticket_dates(
        env,
        ticket_7,
        create_dt=now - timedelta(days=7),
        assigned_dt=now - timedelta(days=7),
        last_stage_dt=now - timedelta(days=6),
        closed_dt=now - timedelta(days=1),
        sla_deadline=now - timedelta(days=2),
    )
    env.invalidate_all()

    env["helpdesk.sla"].check_sla()
    ticket_1.write({"sla_deadline": now + timedelta(days=1), "sla_expired": False})
    ticket_2.write({"sla_deadline": now + timedelta(days=2), "sla_expired": False})
    ticket_3.write({"sla_deadline": now - timedelta(days=2), "sla_expired": True})
    ticket_4.write({"sla_deadline": now + timedelta(days=1), "sla_expired": False})
    ticket_5.write({"sla_deadline": now - timedelta(days=8), "sla_expired": False})
    ticket_6.write({"sla_deadline": now + timedelta(days=2), "sla_expired": False})
    ticket_7.write({"sla_deadline": now - timedelta(days=2), "sla_expired": False})
    support_team.close_team_inactive_tickets()

    ticket_5.rating_send_request(rating_template, force_send=False)
    if ticket_5.rating_ids:
        ticket_5.rating_ids[0].write(
            {
                "rating": 5,
                "feedback": "Fast response and clear billing explanation.",
                "consumed": True,
            }
        )

    env["ir.config_parameter"].sudo().set_param(MODULE_FLAG, "1")

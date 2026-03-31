from odoo import SUPERUSER_ID, api


def _get_or_create_asset(env, values):
    asset = env["helpdesk.support.asset"].search(
        [("name", "=", values["name"])],
        limit=1,
    )
    if asset:
        asset.write(values)
        return asset
    return env["helpdesk.support.asset"].create(values)


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

    contracts = {
        contract.name: contract
        for contract in env["helpdesk.support.contract"].search(
            [("name", "in", [
                "[DEMO] Gold Retainer March 2026",
                "[DEMO] Branch Operations Support Pack",
            ])]
        )
    }
    partners = {
        partner.name: partner
        for partner in env["res.partner"].search(
            [("name", "in", [
                "[DEMO] PT Arunika Logistik",
                "[DEMO] PT Nusantara Retail",
            ])]
        )
    }

    finance_branch = _get_or_create_asset(
        env,
        {
            "name": "[DEMO] Finance HQ Billing Workflow",
            "partner_id": partners.get("[DEMO] PT Arunika Logistik", env["res.partner"]).id,
            "support_contract_id": contracts.get("[DEMO] Gold Retainer March 2026", env["helpdesk.support.contract"]).id,
            "asset_type": "business_process",
            "site_name": "Finance HQ",
            "reference_code": "FIN-HQ-BILLING",
            "location": "Jakarta Finance Shared Service",
            "service_level": "premium",
            "state": "active",
            "notes": "<p>Billing workflow and invoice posting process covered under the gold retainer.</p>",
        },
    )
    pos_terminal = _get_or_create_asset(
        env,
        {
            "name": "[DEMO] Branch A POS Terminal 03",
            "partner_id": partners.get("[DEMO] PT Nusantara Retail", env["res.partner"]).id,
            "asset_type": "device",
            "site_name": "Branch A",
            "reference_code": "POS-BRA-03",
            "serial_number": "SN-POS-0003",
            "location": "Nusantara Retail Branch A",
            "service_level": "standard",
            "state": "active",
            "notes": "<p>Main POS terminal used for branch checkout synchronization monitoring.</p>",
        },
    )
    portal_site = _get_or_create_asset(
        env,
        {
            "name": "[DEMO] Branch Manager Portal Workspace",
            "partner_id": partners.get("[DEMO] PT Nusantara Retail", env["res.partner"]).id,
            "support_contract_id": contracts.get("[DEMO] Branch Operations Support Pack", env["helpdesk.support.contract"]).id,
            "asset_type": "portal_access",
            "site_name": "Retail HQ",
            "reference_code": "PORTAL-BRANCH-MGR",
            "location": "Nusantara Retail HQ",
            "service_level": "standard",
            "state": "active",
            "notes": "<p>Portal role access and branch manager onboarding scope.</p>",
        },
    )
    warehouse_site = _get_or_create_asset(
        env,
        {
            "name": "[DEMO] Warehouse Discovery Zone",
            "partner_id": partners.get("[DEMO] PT Nusantara Retail", env["res.partner"]).id,
            "asset_type": "site",
            "site_name": "Warehouse",
            "reference_code": "SITE-WH-DISCOVERY",
            "location": "Customer branch warehouse",
            "service_level": "standard",
            "state": "inactive",
            "notes": "<p>Warehouse site pending access readiness for discovery and inspection follow-up.</p>",
        },
    )

    tickets_by_name = {
        ticket.name: ticket
        for ticket in env["helpdesk.ticket"].search(
            [("name", "in", [
                "[DEMO] Cannot post invoice to customer",
                "[DEMO] POS sync error after patch",
                "[DEMO] POS sync error after patch (duplicate)",
                "[DEMO] Need new portal access for branch manager",
                "[DEMO] CRM lead follow-up from support case",
            ])]
        )
    }
    if finance_branch and tickets_by_name.get("[DEMO] Cannot post invoice to customer"):
        tickets_by_name["[DEMO] Cannot post invoice to customer"].write(
            {"support_asset_id": finance_branch.id}
        )
    if pos_terminal:
        for name in [
            "[DEMO] POS sync error after patch",
            "[DEMO] POS sync error after patch (duplicate)",
        ]:
            ticket = tickets_by_name.get(name)
            if ticket:
                ticket.write({"support_asset_id": pos_terminal.id})
    if portal_site and tickets_by_name.get("[DEMO] Need new portal access for branch manager"):
        tickets_by_name["[DEMO] Need new portal access for branch manager"].write(
            {"support_asset_id": portal_site.id}
        )
    if warehouse_site and tickets_by_name.get("[DEMO] CRM lead follow-up from support case"):
        tickets_by_name["[DEMO] CRM lead follow-up from support case"].write(
            {"support_asset_id": warehouse_site.id}
        )

    dispatch_asset_map = {
        "[DEMO] Emergency POS Branch Visit": pos_terminal,
        "[DEMO] Finance Workflow Validation Session": finance_branch,
        "[DEMO] Branch Manager Portal Onboarding": portal_site,
        "[DEMO] Discovery Visit Follow-up": warehouse_site,
    }
    for dispatch in env["helpdesk.dispatch"].search([("name", "in", list(dispatch_asset_map.keys()))]):
        asset = dispatch_asset_map.get(dispatch.name)
        if asset:
            dispatch.write({"support_asset_id": asset.id})

    env.cr.commit()

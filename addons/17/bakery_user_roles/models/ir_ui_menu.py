from odoo import api, models


MENU_GROUP_XMLIDS = {
    "base.menu_administration": [
        "base.group_system",
    ],
    "base.menu_management": [
        "base.group_system",
    ],
    "base.menu_apps": [
        "base.group_system",
    ],
    "base.menu_module_tree": [
        "base.group_system",
    ],
    "base.menu_third_party": [
        "base.group_system",
    ],
    "base.menu_view_base_module_update": [
        "base.group_system",
    ],
    "base.menu_tests": [
        "base.group_system",
    ],
    "utm.menu_link_tracker_root": [
        "base.group_system",
    ],
    "mail.menu_root_discuss": [
        "base.group_system",
        "bakery_user_roles.group_bakery_purchase_user",
        "bakery_user_roles.group_bakery_purchase_manager",
        "bakery_user_roles.group_bakery_warehouse_user",
        "bakery_user_roles.group_bakery_warehouse_admin",
        "bakery_user_roles.group_bakery_baker_user",
        "bakery_user_roles.group_bakery_baker_supervisor",
        "bakery_user_roles.group_bakery_cashier",
        "bakery_user_roles.group_bakery_cashier_supervisor",
        "bakery_user_roles.group_bakery_finance",
        "bakery_user_roles.group_bakery_owner",
    ],
    "account.menu_finance": [
        "base.group_system",
        "bakery_user_roles.group_bakery_finance",
        "bakery_user_roles.group_bakery_owner",
    ],
    "account_accountant.menu_accounting": [
        "base.group_system",
        "bakery_user_roles.group_bakery_finance",
        "bakery_user_roles.group_bakery_owner",
    ],
    "spreadsheet_dashboard.spreadsheet_dashboard_menu_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_finance",
        "bakery_user_roles.group_bakery_owner",
    ],
    "stock.menu_stock_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_warehouse_user",
        "bakery_user_roles.group_bakery_warehouse_admin",
        "bakery_user_roles.group_bakery_baker_user",
        "bakery_user_roles.group_bakery_baker_supervisor",
        "bakery_user_roles.group_bakery_owner",
    ],
    "purchase.menu_purchase_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_purchase_user",
        "bakery_user_roles.group_bakery_purchase_manager",
        "bakery_user_roles.group_bakery_owner",
    ],
    "purchase_request.parent_menu_purchase_request": [
        "base.group_system",
        "bakery_user_roles.group_bakery_purchase_user",
        "bakery_user_roles.group_bakery_purchase_manager",
        "bakery_user_roles.group_bakery_owner",
    ],
    "contacts.menu_contacts": [
        "base.group_system",
        "bakery_user_roles.group_bakery_purchase_user",
        "bakery_user_roles.group_bakery_purchase_manager",
        "bakery_user_roles.group_bakery_warehouse_user",
        "bakery_user_roles.group_bakery_warehouse_admin",
        "bakery_user_roles.group_bakery_baker_user",
        "bakery_user_roles.group_bakery_baker_supervisor",
        "bakery_user_roles.group_bakery_cashier",
        "bakery_user_roles.group_bakery_cashier_supervisor",
        "bakery_user_roles.group_bakery_finance",
        "bakery_user_roles.group_bakery_owner",
    ],
    "hr.menu_hr_root": [
        "base.group_system",
    ],
    "mrp.menu_mrp_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_baker_user",
        "bakery_user_roles.group_bakery_baker_supervisor",
        "bakery_user_roles.group_bakery_owner",
    ],
    "mrp_workorder.menu_mrp_workorder_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_baker_user",
        "bakery_user_roles.group_bakery_baker_supervisor",
        "bakery_user_roles.group_bakery_owner",
    ],
    "point_of_sale.menu_point_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_cashier",
        "bakery_user_roles.group_bakery_cashier_supervisor",
        "bakery_user_roles.group_bakery_owner",
    ],
    "pos_preparation_display.menu_point_kitchen_display_root": [
        "base.group_system",
        "bakery_user_roles.group_bakery_cashier",
        "bakery_user_roles.group_bakery_cashier_supervisor",
        "bakery_user_roles.group_bakery_owner",
    ],
    "sale.sale_menu_root": [
        "base.group_system",
    ],
    "hr_work_entry_contract_enterprise.menu_hr_payroll_root": [
        "base.group_system",
    ],
    "membership.menu_association": [
        "base.group_system",
    ],
}


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    @api.model
    def apply_bakery_role_menu_restrictions(self):
        for menu_xmlid, group_xmlids in MENU_GROUP_XMLIDS.items():
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if not menu:
                continue

            group_ids = []
            for group_xmlid in group_xmlids:
                group = self.env.ref(group_xmlid, raise_if_not_found=False)
                if group:
                    group_ids.append(group.id)

            if group_ids:
                menu.sudo().write({"groups_id": [(6, 0, group_ids)]})

DEFAULT_PASSWORD = "ChangeMe123!"

ROLE_USER_SPECS = [
    ("purchase.user", "Purchase User", "bakery_user_roles.group_bakery_purchase_user"),
    ("purchase.manager", "Purchase Manager", "bakery_user_roles.group_bakery_purchase_manager"),
    ("warehouse.user", "Warehouse User", "bakery_user_roles.group_bakery_warehouse_user"),
    ("warehouse.admin", "Warehouse Admin", "bakery_user_roles.group_bakery_warehouse_admin"),
    ("baker.user", "Baker User", "bakery_user_roles.group_bakery_baker_user"),
    ("baker.supervisor", "Baker Supervisor", "bakery_user_roles.group_bakery_baker_supervisor"),
    ("cashier.user", "Cashier", "bakery_user_roles.group_bakery_cashier"),
    ("cashier.supervisor", "Cashier Supervisor", "bakery_user_roles.group_bakery_cashier_supervisor"),
    ("finance.user", "Finance", "bakery_user_roles.group_bakery_finance"),
    ("owner.user", "Owner", "bakery_user_roles.group_bakery_owner"),
    ("investor.portal", "Investor Portal", "bakery_user_roles.group_bakery_investor_portal"),
]


def _upsert_role_user(env, login, name, role_group_xmlid):
    users = env["res.users"].sudo().with_context(no_reset_password=True)
    role_group = env.ref(role_group_xmlid)
    user = users.search([("login", "=", login)], limit=1)

    vals = {
        "name": name,
        "groups_id": [(6, 0, [role_group.id])],
    }

    if user:
        user.write(vals)
        return user

    vals.update(
        {
            "login": login,
            "password": DEFAULT_PASSWORD,
            "company_id": env.company.id,
            "company_ids": [(6, 0, env.user.company_ids.ids)],
        }
    )
    return users.create(vals)


def post_init_hook(env):
    for login, name, role_group_xmlid in ROLE_USER_SPECS:
        _upsert_role_user(env, login, name, role_group_xmlid)

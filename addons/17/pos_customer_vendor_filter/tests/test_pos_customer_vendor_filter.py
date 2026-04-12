from unittest.mock import patch

from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.tests import new_test_user
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestPosCustomerVendorFilter(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_customer_only = cls.env["res.partner"].create(
            {
                "name": "POS Partner Customer Only",
                "customer_rank": 1,
                "supplier_rank": 0,
            }
        )
        cls.partner_vendor_only = cls.env["res.partner"].create(
            {
                "name": "POS Partner Vendor Only",
                "customer_rank": 0,
                "supplier_rank": 1,
            }
        )
        cls.partner_both = cls.env["res.partner"].create(
            {
                "name": "POS Partner Customer Vendor",
                "customer_rank": 1,
                "supplier_rank": 1,
            }
        )
        cls.partner_neutral = cls.env["res.partner"].create(
            {
                "name": "POS Partner Neutral",
                "customer_rank": 0,
                "supplier_rank": 0,
            }
        )
        cls.internal_user = new_test_user(
            cls.env,
            login="pos_internal_partner_user",
            groups="base.group_user",
            company_id=cls.company.id,
            company_ids=[(6, 0, cls.company.ids)],
        )
        cls.partner_internal_user = cls.internal_user.partner_id

    def test_loader_domain_excludes_vendor_only_partner(self):
        session = self.open_new_session()
        params = session._loader_params_res_partner()
        domain = params["search_params"]["domain"]
        partners = self.env["res.partner"].search(domain)

        self.assertIn(self.partner_customer_only, partners)
        self.assertIn(self.partner_both, partners)
        self.assertIn(self.partner_neutral, partners)
        self.assertNotIn(self.partner_vendor_only, partners)
        self.assertNotIn(self.partner_internal_user, partners)

    def test_pos_ui_loader_excludes_vendor_only_partner(self):
        session = self.open_new_session()
        partner_rows = [
            (self.partner_customer_only.id,),
            (self.partner_vendor_only.id,),
            (self.partner_both.id,),
            (self.partner_neutral.id,),
            (self.partner_internal_user.id,),
        ]
        with patch.object(
            type(session.config_id),
            "get_limited_partners_loading",
            return_value=partner_rows,
        ):
            partners = session._get_pos_ui_res_partner(session._loader_params_res_partner())
        partner_ids = {partner["id"] for partner in partners}

        self.assertIn(self.partner_customer_only.id, partner_ids)
        self.assertIn(self.partner_both.id, partner_ids)
        self.assertIn(self.partner_neutral.id, partner_ids)
        self.assertNotIn(self.partner_vendor_only.id, partner_ids)
        self.assertNotIn(self.partner_internal_user.id, partner_ids)

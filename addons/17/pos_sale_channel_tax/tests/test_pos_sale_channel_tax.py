from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosSaleChannelTax(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["pos.config"].search([], limit=1)
        cls.company = cls.config.company_id
        cls.channel_tax = cls.env["account.tax"].create(
            {
                "name": "Channel Tax Test",
                "company_id": cls.company.id,
                "type_tax_use": "sale",
                "amount_type": "percent",
                "amount": 10,
            }
        )
        cls.dine_in_channel = cls.env["pos.sale.channel"].search([("name", "=", "Dine In")], limit=1)
        cls.dine_in_channel.channel_tax_id = cls.channel_tax

    @classmethod
    def _make_session(cls):
        return cls.env["pos.session"].new(
            {
                "config_id": cls.config.id,
                "company_id": cls.company.id,
            }
        )

    def test_sale_channel_loader_includes_tax_field(self):
        params = self._make_session()._loader_params_pos_sale_channel()

        self.assertIn("channel_tax_id", params["search_params"]["fields"])

    def test_channel_tax_is_loaded_even_if_not_available_manually(self):
        session = self._make_session()
        taxes = session._get_pos_ui_account_tax(session._loader_params_account_tax())
        tax_ids = {tax["id"] for tax in taxes}

        self.assertIn(self.channel_tax.id, tax_ids)

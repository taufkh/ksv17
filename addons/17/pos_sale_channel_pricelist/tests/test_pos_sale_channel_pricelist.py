from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPosSaleChannelPricelist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["pos.config"].search([], limit=1)
        if not cls.config.pricelist_id:
            cls.default_pricelist = cls.env["product.pricelist"].create(
                {
                    "name": "POS Default Pricelist Test",
                    "currency_id": cls.config.company_id.currency_id.id,
                }
            )
            cls.config.write({"pricelist_id": cls.default_pricelist.id})
        else:
            cls.default_pricelist = cls.config.pricelist_id
        cls.grab_channel = cls.env["pos.sale.channel"].search([("name", "=", "GrabFood")], limit=1)
        cls.other_channel = cls.env["pos.sale.channel"].search([("name", "=", "Other")], limit=1)
        cls.grab_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "GrabFood Pricelist Test",
                "currency_id": cls.config.company_id.currency_id.id,
            }
        )

        cls.grab_channel.pricelist_id = cls.grab_pricelist
        cls.other_channel.pricelist_id = False

    @classmethod
    def _make_session(cls):
        return cls.env["pos.session"].new(
            {
                "config_id": cls.config.id,
                "company_id": cls.config.company_id.id,
            }
        )

    def test_sale_channel_loader_includes_pricelist_field(self):
        params = self._make_session()._loader_params_pos_sale_channel()

        self.assertIn("pricelist_id", params["search_params"]["fields"])

    def test_channel_pricelist_is_loaded_even_if_not_available_manually(self):
        self.config.write(
            {
                "use_pricelist": True,
                "available_pricelist_ids": [(6, 0, self.default_pricelist.ids)],
            }
        )

        session = self._make_session()
        pricelists = session._get_pos_ui_product_pricelist(session._loader_params_product_pricelist())
        pricelist_ids = {pricelist["id"] for pricelist in pricelists}

        self.assertIn(self.default_pricelist.id, pricelist_ids)
        self.assertIn(self.grab_pricelist.id, pricelist_ids)

    def test_default_pricelist_stays_loaded_when_pos_pricelist_feature_disabled(self):
        self.config.write({"use_pricelist": False})

        session = self._make_session()
        pricelists = session._get_pos_ui_product_pricelist(session._loader_params_product_pricelist())
        pricelist_ids = {pricelist["id"] for pricelist in pricelists}

        self.assertIn(self.default_pricelist.id, pricelist_ids)
        self.assertIn(self.grab_pricelist.id, pricelist_ids)
        self.assertFalse(self.other_channel.pricelist_id)

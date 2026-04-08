from odoo import fields, models, tools


class PosAutoScrapDailyReport(models.Model):
    _name = "pos.auto.scrap.daily.report"
    _description = "POS Auto Scrap Daily Report"
    _auto = False
    _order = "report_date desc, pos_config_id, product_id"
    _rec_name = "product_id"

    report_date = fields.Date(string="Report Date", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        readonly=True,
    )
    pos_config_id = fields.Many2one("pos.config", string="Point of Sale", readonly=True)
    pos_session_id = fields.Many2one("pos.session", string="Session", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    product_tmpl_id = fields.Many2one("product.template", string="Product Template", readonly=True)
    sold_qty = fields.Float(string="Sold Qty", readonly=True)
    scrapped_qty = fields.Float(string="Scrapped Qty", readonly=True)
    prepared_qty = fields.Float(string="Prepared Qty", readonly=True)
    loss_value = fields.Monetary(
        string="Loss Value",
        currency_field="currency_id",
        readonly=True,
    )
    waste_rate = fields.Float(string="Waste Rate (%)", readonly=True, digits=(16, 2))

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH auto_scrap_source AS (
                    SELECT
                        pol.id AS id,
                        COALESCE(ps.stop_at::date, ps.start_at::date) AS report_date,
                        po.company_id AS company_id,
                        ps.config_id AS pos_config_id,
                        ps.id AS pos_session_id,
                        pol.product_id AS product_id,
                        pp.product_tmpl_id AS product_tmpl_id,
                        pol.qty AS sold_qty,
                        0.0 AS scrapped_qty,
                        0.0 AS loss_value
                    FROM pos_order_line pol
                    JOIN pos_order po ON po.id = pol.order_id
                    JOIN pos_session ps ON ps.id = po.session_id
                    JOIN product_product pp ON pp.id = pol.product_id
                    JOIN product_template pt ON pt.id = pp.product_tmpl_id
                    WHERE
                        po.state != 'cancel'
                        AND pol.qty > 0
                        AND pt.auto_scrap_on_pos_closing = TRUE

                    UNION ALL

                    SELECT
                        -ss.id AS id,
                        COALESCE(ps.stop_at::date, ps.start_at::date) AS report_date,
                        ss.company_id AS company_id,
                        ss.pos_config_id AS pos_config_id,
                        ss.pos_session_id AS pos_session_id,
                        ss.product_id AS product_id,
                        pp.product_tmpl_id AS product_tmpl_id,
                        0.0 AS sold_qty,
                        ss.scrap_qty AS scrapped_qty,
                        ss.loss_value AS loss_value
                    FROM stock_scrap ss
                    JOIN pos_session ps ON ps.id = ss.pos_session_id
                    JOIN product_product pp ON pp.id = ss.product_id
                    WHERE
                        ss.state = 'done'
                        AND ss.pos_session_id IS NOT NULL
                )
                SELECT
                    MIN(id) AS id,
                    report_date,
                    company_id,
                    pos_config_id,
                    pos_session_id,
                    product_id,
                    product_tmpl_id,
                    SUM(sold_qty) AS sold_qty,
                    SUM(scrapped_qty) AS scrapped_qty,
                    SUM(sold_qty) + SUM(scrapped_qty) AS prepared_qty,
                    SUM(loss_value) AS loss_value,
                    CASE
                        WHEN SUM(sold_qty) + SUM(scrapped_qty) = 0 THEN 0.0
                        ELSE (SUM(scrapped_qty) / (SUM(sold_qty) + SUM(scrapped_qty))) * 100.0
                    END AS waste_rate
                FROM auto_scrap_source
                GROUP BY
                    report_date,
                    company_id,
                    pos_config_id,
                    pos_session_id,
                    product_id,
                    product_tmpl_id
            )
            """
        )

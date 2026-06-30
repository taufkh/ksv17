from io import BytesIO

from odoo import _, fields, http
from odoo.http import content_disposition, request
from odoo.tools.misc import xlsxwriter


class PosSaleChannelController(http.Controller):
    @http.route("/pos_sale_channel/online_checker_recap/<int:wizard_id>/xlsx", type="http", auth="user")
    def export_online_checker_recap_xlsx(self, wizard_id, **kwargs):
        wizard = request.env["pos.online.checker.recap.wizard"].browse(wizard_id)
        if not wizard.exists() or not request.env.user.has_group("point_of_sale.group_pos_user"):
            return request.render(
                "http_routing.http_error",
                {
                    "status_code": "Oops",
                    "status_message": _(
                        "You do not have access to export the online checker recap report."
                    ),
                },
            )

        orders = wizard._get_report_orders()
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Online Checker Recap")

        title_style = workbook.add_format({"bold": True, "font_size": 14})
        header_style = workbook.add_format(
            {"bold": True, "bg_color": "#D9EAD3", "border": 1, "align": "center", "valign": "vcenter"}
        )
        text_style = workbook.add_format({"border": 1, "valign": "top"})
        datetime_style = workbook.add_format({"border": 1, "num_format": "yyyy-mm-dd hh:mm:ss", "valign": "top"})
        amount_style = workbook.add_format({"border": 1, "num_format": "#,##0.00", "valign": "top"})
        summary_label_style = workbook.add_format({"bold": True})

        worksheet.write(0, 0, _("Online Checker Recap"), title_style)
        worksheet.write(2, 0, _("Date From"), summary_label_style)
        worksheet.write(2, 1, str(wizard.date_from or ""))
        worksheet.write(3, 0, _("Date To"), summary_label_style)
        worksheet.write(3, 1, str(wizard.date_to or ""))
        worksheet.write(2, 3, _("Point of Sale"), summary_label_style)
        worksheet.write(2, 4, ", ".join(wizard.config_ids.mapped("name")) or _("All"))
        worksheet.write(3, 3, _("Sales Channels"), summary_label_style)
        worksheet.write(3, 4, ", ".join(wizard.sale_channel_ids.mapped("name")) or _("All"))
        worksheet.write(4, 3, _("Checker Status"), summary_label_style)
        worksheet.write(4, 4, wizard._get_status_label())

        headers = [
            _("Order Date"),
            _("Order"),
            _("POS"),
            _("Sales Channel"),
            _("Customer"),
            _("Cashier"),
            _("Total"),
            _("Checker Status"),
            _("Progress"),
            _("Pickup / Driver Note"),
            _("Completed At"),
            _("Completed By"),
            _("Override At"),
            _("Override By"),
            _("Override Reason"),
        ]
        widths = [20, 20, 22, 18, 20, 18, 14, 16, 18, 28, 20, 18, 20, 18, 28]

        header_row = 6
        for col, (header, width) in enumerate(zip(headers, widths)):
            worksheet.write(header_row, col, header, header_style)
            worksheet.set_column(col, col, width)

        row = header_row + 1
        for order in orders:
            worksheet.write_datetime(row, 0, fields.Datetime.to_datetime(order.date_order), datetime_style)
            worksheet.write(row, 1, order.name or "", text_style)
            worksheet.write(row, 2, order.config_id.display_name or "", text_style)
            worksheet.write(row, 3, order.sale_channel_id.display_name or "", text_style)
            worksheet.write(row, 4, order.partner_id.display_name or "", text_style)
            worksheet.write(row, 5, order.user_id.display_name or "", text_style)
            worksheet.write_number(row, 6, order.amount_total or 0.0, amount_style)
            worksheet.write(row, 7, dict(order._fields["online_check_status"].selection).get(order.online_check_status, order.online_check_status or ""), text_style)
            worksheet.write(row, 8, order.online_check_progress_display or "", text_style)
            worksheet.write(row, 9, order.online_check_note or "", text_style)
            if order.online_check_completed_at:
                worksheet.write_datetime(row, 10, fields.Datetime.to_datetime(order.online_check_completed_at), datetime_style)
            else:
                worksheet.write(row, 10, "", text_style)
            worksheet.write(row, 11, order.online_check_completed_by_id.display_name or "", text_style)
            if order.online_check_override_at:
                worksheet.write_datetime(row, 12, fields.Datetime.to_datetime(order.online_check_override_at), datetime_style)
            else:
                worksheet.write(row, 12, "", text_style)
            worksheet.write(row, 13, order.online_check_override_by_id.display_name or "", text_style)
            worksheet.write(row, 14, order.online_check_override_reason or "", text_style)
            row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        filename = "online_checker_recap.xlsx"
        return request.make_response(
            xlsx_data,
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", content_disposition(filename)),
            ],
        )

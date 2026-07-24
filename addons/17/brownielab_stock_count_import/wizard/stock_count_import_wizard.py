import base64
import csv
import io
import math
import re
import zipfile
from xml.etree import ElementTree

import xlrd

from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import xlsxwriter


class BrownielabStockCountImportWizard(models.TransientModel):
    _name = "brownielab.stock.count.import.wizard"
    _description = "Brownielab Stock Count Import Wizard"

    location_id = fields.Many2one(
        "stock.location",
        string="Default Location",
        required=True,
        domain=[("usage", "=", "internal")],
        default=lambda self: self.env.ref("stock.stock_location_stock", raise_if_not_found=False),
    )
    inventory_date = fields.Date(
        string="Inventory Date",
        required=True,
        default=fields.Date.context_today,
    )
    apply_immediately = fields.Boolean(
        string="Apply Immediately",
        help="If enabled, the created inventory adjustment lines are applied right after import.",
    )
    upload_file = fields.Binary(string="Import File")
    upload_filename = fields.Char(string="Filename")
    template_notes = fields.Text(
        string="Template Notes",
        readonly=True,
        default=lambda self: self._default_template_notes(),
    )

    def _default_template_notes(self):
        return _(
            "1 file = 1 location.\n"
            "- Choose the location in the wizard, then download the template for that location.\n"
            "- The template already lists all relevant products, including new products that never appeared in stock opname before.\n"
            "- The only input column for users is `counted_pack_qty`, matching the `Counted Pack Qty` column in Inventory Adjustments.\n"
            "- Do not change `default_code`, `product_name`, or `packaging_name`.\n"
            "- The location is determined by the wizard, so it does not appear in the file.\n"
            "- This template is intentionally minimal to avoid ambiguity for non-technical users."
        )

    def action_download_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": f"/brownielab_stock_count_import/template/{self.id}",
            "target": "self",
        }

    def action_import_file(self):
        self.ensure_one()
        rows = self._read_rows()
        if not rows:
            raise UserError(_("The import file is empty."))

        Quant = self.env["stock.quant"].with_context(inventory_mode=True)
        imported_quants = self.env["stock.quant"]
        errors = []

        for index, row in enumerate(rows, start=2):
            try:
                imported_quants |= self._import_row(Quant, row, index)
            except (UserError, ValidationError) as exc:
                errors.append(_("Row %(row)s: %(error)s", row=index, error=exc))

        if errors:
            raise UserError("\n".join(errors[:20]))

        if self.apply_immediately and imported_quants:
            imported_quants.action_apply_inventory()

        return {"type": "ir.actions.act_window_close"}

    def _get_template_products(self):
        return self.env["product.product"].search(
            [
                ("active", "=", True),
                ("detailed_type", "in", ["product", "consu"]),
            ],
            order="default_code, name, id",
        )

    def _import_row(self, Quant, row, row_number):
        product = self._resolve_product(row)
        location = self._resolve_location(row)
        lot = self._resolve_lot(product, row)
        packaging = self._resolve_packaging(product, row)
        counted_pack_qty = self._get_optional_float(row, "counted_pack_qty")
        counted_quantity = self._get_optional_float(row, "counted_quantity")

        if counted_pack_qty is None:
            raise UserError(_("`counted_pack_qty` must be filled for every row."))

        if counted_pack_qty is not None and not packaging:
            raise UserError(
                _(
                    "A default count packaging is required for this item before it can be imported with counted pack quantity."
                )
            )

        if packaging and counted_pack_qty is not None:
            packaging_qty = packaging.product_uom_id._compute_quantity(packaging.qty, product.uom_id)
            computed_quantity = packaging_qty * counted_pack_qty
            if counted_quantity is not None and float_compare(
                counted_quantity,
                computed_quantity,
                precision_rounding=product.uom_id.rounding,
            ):
                raise UserError(
                    _(
                        "counted_quantity does not match counted_pack_qty multiplied by the selected packaging quantity."
                    )
                )
            counted_quantity = computed_quantity

        if counted_quantity is None:
            raise UserError(_("counted_quantity could not be determined for this row."))

        quant = self._find_existing_quant(Quant, product, location, lot)
        vals = {
            "product_id": product.id,
            "location_id": location.id,
            "inventory_date": self.inventory_date,
            "inventory_quantity": counted_quantity,
        }
        if lot:
            vals["lot_id"] = lot.id
        if packaging:
            vals["inventory_packaging_id"] = packaging.id
            vals["inventory_pack_qty"] = counted_pack_qty if counted_pack_qty is not None else 0.0

        if quant:
            quant.write(vals)
        else:
            quant = Quant.create(vals)
        return quant

    def _find_existing_quant(self, Quant, product, location, lot):
        domain = [
            ("product_id", "=", product.id),
            ("location_id", "=", location.id),
            ("company_id", "=", self.env.company.id),
            ("package_id", "=", False),
            ("owner_id", "=", False),
        ]
        if lot:
            domain.append(("lot_id", "=", lot.id))
        else:
            domain.append(("lot_id", "=", False))
        return Quant.search(domain, limit=1)

    def _resolve_product(self, row):
        Product = self.env["product.product"]
        default_code = (row.get("default_code") or "").strip()
        barcode = (row.get("product_barcode") or "").strip()
        product = Product
        if default_code:
            product = Product.search([("default_code", "=", default_code)], limit=2)
            if not product:
                raise UserError(_("Product with internal reference `%s` was not found.") % default_code)
        elif barcode:
            product = Product.search([("barcode", "=", barcode)], limit=2)
            if not product:
                raise UserError(_("Product with barcode `%s` was not found.") % barcode)
        else:
            raise UserError(_("default_code is required unless product_barcode is filled."))
        if len(product) > 1:
            raise UserError(_("More than one product matches this row."))
        return product

    def _resolve_location(self, row):
        StockLocation = self.env["stock.location"]
        location_code = (row.get("location_code") or "").strip()
        location_name = (row.get("location_name") or "").strip()
        if not location_code and not location_name:
            return self.location_id
        domain = [("usage", "=", "internal")]
        if location_code:
            location = StockLocation.search(domain + [("barcode", "=", location_code)], limit=2)
            if not location:
                location = StockLocation.search(domain + [("complete_name", "=", location_code)], limit=2)
            if not location:
                location = StockLocation.search(domain + [("name", "=", location_code)], limit=2)
        else:
            location = StockLocation.search(domain + [("complete_name", "=", location_name)], limit=2)
            if not location:
                location = StockLocation.search(domain + [("name", "=", location_name)], limit=2)
        if not location:
            raise UserError(_("The location in this row was not found."))
        if len(location) > 1:
            raise UserError(_("The location in this row is ambiguous. Use a more specific location code."))
        return location

    def _get_template_packaging(self, product):
        packaging = self.env["product.packaging"]
        if "inventory_is_default" in self.env["product.packaging"]._fields:
            packaging = product.packaging_ids.filtered("inventory_is_default")[:1]
        if not packaging and len(product.packaging_ids) == 1:
            packaging = product.packaging_ids
        return packaging[:1]

    def _resolve_lot(self, product, row):
        lot_name = (row.get("lot_name") or "").strip()
        if product.tracking == "none":
            return self.env["stock.lot"]
        if not lot_name:
            raise UserError(_("This tracked product requires lot_name or serial number in the import file."))
        lot = self.env["stock.lot"].search(
            [("product_id", "=", product.id), ("name", "=", lot_name), ("company_id", "=", self.env.company.id)],
            limit=2,
        )
        if not lot:
            raise UserError(_("Lot/serial `%s` was not found for this product.") % lot_name)
        if len(lot) > 1:
            raise UserError(_("Lot/serial `%s` is ambiguous for this product.") % lot_name)
        return lot

    def _resolve_packaging(self, product, row):
        packaging_barcode = (row.get("packaging_barcode") or "").strip()
        packaging_name = (row.get("packaging_name") or "").strip()
        packaging = self.env["product.packaging"]
        if packaging_barcode:
            packaging = product.packaging_ids.filtered(lambda pack: (pack.barcode or "").strip() == packaging_barcode)
            if not packaging:
                raise UserError(
                    _("Packaging barcode `%s` was not found on product `%s`.") % (packaging_barcode, product.display_name)
                )
        elif packaging_name:
            normalized_name = packaging_name.casefold()
            packaging = product.packaging_ids.filtered(
                lambda pack: (pack.name or "").strip().casefold() == normalized_name
            )
            if not packaging:
                raise UserError(
                    _("Packaging `%s` was not found on product `%s`.") % (packaging_name, product.display_name)
                )
        else:
            if "inventory_is_default" in self.env["product.packaging"]._fields:
                packaging = product.packaging_ids.filtered("inventory_is_default")[:1]
            if not packaging and len(product.packaging_ids) == 1:
                packaging = product.packaging_ids
        if len(packaging) > 1:
            raise UserError(
                _(
                    "More than one packaging matches product `%s`. Use packaging_barcode to make the row explicit."
                )
                % product.display_name
            )
        return packaging[:1]

    def _read_rows(self):
        self.ensure_one()
        if not self.upload_file:
            raise UserError(_("Please upload an import file first."))

        filename = (self.upload_filename or "").lower()
        content = base64.b64decode(self.upload_file)
        if filename.endswith(".csv"):
            return self._read_csv_rows(content)
        if filename.endswith(".xlsx"):
            return self._read_excel_rows(content)
        if filename.endswith(".xls"):
            return self._read_xls_rows(content)
        raise UserError(_("Unsupported file format. Please upload a .csv, .xls, or .xlsx file."))

    def _read_csv_rows(self, content):
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return [self._normalize_row(row) for row in reader if any((value or "").strip() for value in row.values())]

    def _read_excel_rows(self, content):
        namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            shared_strings = self._read_xlsx_shared_strings(archive, namespace)
            sheet_name = self._get_first_xlsx_sheet_path(archive)
            root = ElementTree.fromstring(archive.read(sheet_name))
        rows = []
        header_row = []
        for row_index, row_node in enumerate(root.findall(".//main:sheetData/main:row", namespace)):
            cells = {}
            for cell in row_node.findall("main:c", namespace):
                reference = cell.get("r", "")
                column_index = self._xlsx_column_index(reference)
                cells[column_index] = self._read_xlsx_cell_value(cell, shared_strings, namespace)
            if row_index == 0:
                header_row = [self._normalize_header(cells.get(index, "")) for index in range(max(cells.keys(), default=-1) + 1)]
                continue
            if not header_row:
                continue
            values = {}
            has_value = False
            for index, header in enumerate(header_row):
                value = str(cells.get(index, "")).strip()
                values[header] = value
                has_value = has_value or bool(value)
            if has_value:
                rows.append(self._normalize_row(values))
        return rows

    def _read_xls_rows(self, content):
        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(0)
        if sheet.nrows < 2:
            return []
        headers = [self._normalize_header(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
        rows = []
        for row_index in range(1, sheet.nrows):
            values = {}
            has_value = False
            for col_index, header in enumerate(headers):
                cell_value = sheet.cell_value(row_index, col_index)
                if sheet.cell_type(row_index, col_index) == xlrd.XL_CELL_NUMBER:
                    if math.isfinite(cell_value) and float(cell_value).is_integer():
                        cell_value = str(int(cell_value))
                    else:
                        cell_value = str(cell_value)
                else:
                    cell_value = str(cell_value).strip()
                values[header] = cell_value
                has_value = has_value or bool(str(cell_value).strip())
            if has_value:
                rows.append(self._normalize_row(values))
        return rows

    def _normalize_row(self, row):
        return {self._normalize_header(key): (value or "").strip() for key, value in row.items() if key}

    def _normalize_header(self, value):
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower())
        return normalized.strip("_")

    def _get_optional_float(self, row, key):
        value = (row.get(key) or "").strip()
        if not value:
            return None
        try:
            return float(value.replace(",", ""))
        except ValueError as exc:
            raise UserError(_("`%s` must be a number.") % key) from exc

    def _read_xlsx_shared_strings(self, archive, namespace):
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
        strings = []
        for string_node in root.findall("main:si", namespace):
            fragments = []
            for text_node in string_node.findall(".//main:t", namespace):
                fragments.append(text_node.text or "")
            strings.append("".join(fragments))
        return strings

    def _get_first_xlsx_sheet_path(self, archive):
        workbook_root = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        rel_root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        namespace = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rel_namespace = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
        first_sheet = workbook_root.find(".//main:sheets/main:sheet", namespace)
        if first_sheet is None:
            raise UserError(_("The workbook does not contain any worksheet."))
        relationship_id = first_sheet.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        for relation in rel_root.findall("rel:Relationship", rel_namespace):
            if relation.get("Id") == relationship_id:
                return f"xl/{relation.get('Target')}"
        raise UserError(_("The first worksheet could not be resolved from the workbook."))

    def _xlsx_column_index(self, reference):
        letters = "".join(char for char in reference if char.isalpha()).upper()
        index = 0
        for letter in letters:
            index = index * 26 + (ord(letter) - 64)
        return max(index - 1, 0)

    def _read_xlsx_cell_value(self, cell, shared_strings, namespace):
        cell_type = cell.get("t")
        value_node = cell.find("main:v", namespace)
        if cell_type == "inlineStr":
            inline_node = cell.find("main:is/main:t", namespace)
            return inline_node.text if inline_node is not None else ""
        if value_node is None:
            return ""
        raw_value = value_node.text or ""
        if cell_type == "s":
            try:
                return shared_strings[int(raw_value)]
            except (IndexError, ValueError):
                return raw_value
        if cell_type == "b":
            return "1" if raw_value == "1" else "0"
        try:
            numeric_value = float(raw_value)
        except ValueError:
            return raw_value
        if math.isfinite(numeric_value) and numeric_value.is_integer():
            return str(int(numeric_value))
        return str(numeric_value)

    def _build_template_xlsx(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Stock Count")

        header_style = workbook.add_format({"bold": True, "bg_color": "#D9EAD3", "border": 1})
        text_style = workbook.add_format({"border": 1})
        number_style = workbook.add_format({"border": 1, "num_format": "#,##0.00"})
        note_style = workbook.add_format({"font_color": "#666666"})

        headers = [
            "default_code",
            "product_name",
            "packaging_name",
            "counted_pack_qty",
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_style)
            worksheet.set_column(col, col, max(len(header) + 4, 18))

        row = 1
        for product in self._get_template_products():
            packaging = self._get_template_packaging(product)
            values = [
                product.default_code or "",
                product.display_name or product.name or "",
                packaging.name or "" if packaging else "",
                "",
            ]
            for col, value in enumerate(values):
                if isinstance(value, (int, float)) and value != "":
                    worksheet.write_number(row, col, value, number_style)
                else:
                    worksheet.write(row, col, value, text_style)
            row += 1

        worksheet.write(
            row + 1,
            0,
            "This file is generated for location: %s" % (self.location_id.complete_name or self.location_id.display_name),
            note_style,
        )
        worksheet.write(
            row + 2,
            0,
            "Packaging names may repeat across products. The import resolves packaging only after the product is identified.",
            note_style,
        )
        workbook.close()
        return output.getvalue()

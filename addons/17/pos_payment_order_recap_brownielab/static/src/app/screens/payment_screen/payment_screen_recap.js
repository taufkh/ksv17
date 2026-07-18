/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    get brownielabOrderRecapLines() {
        return this.currentOrder.get_orderlines().map((line) => {
            const product = line.get_product();
            const fullProductName = line.get_full_product_name?.();
            const quantity = line.get_quantity();
            const lineTotal = line.get_price_with_tax();
            const note = line.get_note?.() || "";

            return {
                id: line.cid,
                name: fullProductName || product?.display_name || "",
                qty: this._formatBrownielabQty(quantity),
                price: this.env.utils.formatCurrency(lineTotal),
                note,
                isNegative: lineTotal < 0 || quantity < 0,
                isDiscountLine:
                    lineTotal < 0 ||
                    (product?.display_name || "").toLowerCase().includes("discount"),
            };
        });
    },
    get brownielabOrderRecapSummary() {
        const positiveLines = this.currentOrder
            .get_orderlines()
            .filter((line) => line.get_quantity() > 0);
        const totalItems = positiveLines.reduce((sum, line) => sum + line.get_quantity(), 0);
        const totalWithTax = this.currentOrder.get_total_with_tax();
        const totalTax = this.currentOrder.get_total_tax?.() || 0;

        return {
            title: _t("Daftar Pesanan"),
            totalItemsLabel: `${_t("Total item")}: ${this._formatBrownielabQty(totalItems)}`,
            emptyLabel: _t("Belum ada item di transaksi ini."),
            subtotalLabel: _t("Subtotal"),
            totalLabel: _t("Total"),
            subtotalValue: this.env.utils.formatCurrency(totalWithTax - totalTax),
            totalValue: this.env.utils.formatCurrency(totalWithTax),
        };
    },
    _formatBrownielabQty(value) {
        if (Number.isInteger(value)) {
            return value.toString();
        }
        return value.toFixed(2).replace(/\.00$/, "");
    },
});

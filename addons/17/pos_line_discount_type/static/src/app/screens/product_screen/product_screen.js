/** @odoo-module */

import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { NumberPopup } from "@point_of_sale/app/utils/input_popups/number_popup";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ProductScreen.prototype, {
    async onLineDiscountTypeNumpadClick(buttonValue) {
        if (buttonValue !== "discount") {
            return this.onNumpadClick(buttonValue);
        }

        const selectedLine = this.currentOrder?.get_selected_orderline();
        if (!selectedLine) {
            await this.popup.add(ErrorPopup, {
                title: _t("No order line selected"),
                body: _t("Select an order line before applying a discount."),
            });
            return;
        }

        const currentDiscountType = selectedLine.getDiscountType();
        const { confirmed: typeConfirmed, payload: discountType } = await this.popup.add(
            SelectionPopup,
            {
                title: _t("Discount Type"),
                list: [
                    {
                        id: "percent",
                        label: _t("Percentage (%)"),
                        item: "percent",
                        isSelected: currentDiscountType === "percent",
                    },
                    {
                        id: "amount",
                        label: _t("Amount"),
                        item: "amount",
                        isSelected: currentDiscountType === "amount",
                    },
                ],
            }
        );
        if (!typeConfirmed || !discountType) {
            return;
        }

        const { confirmed: valueConfirmed, payload: discountValue } = await this.popup.add(
            NumberPopup,
            {
                title:
                    discountType === "amount"
                        ? _t("Set the discount amount")
                        : _t("Set the discount percentage"),
                startingValue: selectedLine.getDiscountInputValue(discountType),
                isInputSelected: true,
                nbrDecimal: discountType === "amount" ? this.pos.currency.decimal_places : 2,
            }
        );
        if (!valueConfirmed) {
            return;
        }

        await this.pos.setDiscountFromUI(selectedLine, discountValue, discountType);
    },
});

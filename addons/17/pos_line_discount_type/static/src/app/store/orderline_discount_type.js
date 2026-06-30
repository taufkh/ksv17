/** @odoo-module */

import { Orderline } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { _t } from "@web/core/l10n/translation";
import { parseFloat as parseValue } from "@web/views/fields/parsers";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setDiscountFromUI(line, val, discountType = "percent") {
        if (discountType === "amount") {
            line.set_discount_amount(val);
            return;
        }
        line.set_discount(val);
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.discount_type = this.discount_type || "percent";
        this.discount_amount = this.discount_amount || 0;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.discount_type = json.discount_type || "percent";
        this.discount_amount = json.discount_amount || 0;
        if (this.discount_type === "amount") {
            this._syncAmountDiscountToPercentage();
        }
    },
    clone() {
        const orderline = super.clone(...arguments);
        orderline.discount_type = this.discount_type;
        orderline.discount_amount = this.discount_amount;
        return orderline;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.discount_type = this.discount_type || "percent";
        json.discount_amount = this.discount_amount || 0;
        return json;
    },
    set_discount(discount) {
        super.set_discount(discount);
        this.discount_type = "percent";
        this.discount_amount = 0;
    },
    set_discount_amount(amount) {
        const parsedAmount = this._parseDiscountValue(amount);
        const baseAmount = this._getDiscountableBaseAmount();
        const safeAmount = Math.max(parsedAmount || 0, 0);

        this.discount_type = "amount";
        this.discount_amount = Math.min(safeAmount, baseAmount);
        this._syncAmountDiscountToPercentage();
    },
    set_quantity() {
        const result = super.set_quantity(...arguments);
        if (result !== false) {
            this._syncAmountDiscountToPercentage();
        }
        return result;
    },
    set_unit_price() {
        super.set_unit_price(...arguments);
        this._syncAmountDiscountToPercentage();
    },
    getDiscountType() {
        return this.discount_type || "percent";
    },
    getDiscountAmount() {
        return this.discount_amount || 0;
    },
    getDiscountInputValue(discountType = this.getDiscountType()) {
        return discountType === "amount" ? this.getDiscountAmount() : this.get_discount();
    },
    getDisplayData() {
        const result = super.getDisplayData(...arguments);
        return {
            ...result,
            discountType: this.getDiscountType(),
            discountAmount: this.env.utils.formatCurrency(this.getDiscountAmount()),
            discountLabel:
                this.getDiscountType() === "amount"
                    ? _t("Discount: %s", this.env.utils.formatCurrency(this.getDiscountAmount()))
                    : _t("%s With a %s%% discount", result.price_without_discount, result.discount),
        };
    },
    _parseDiscountValue(value) {
        if (typeof value === "number") {
            return value;
        }
        return parseValue((value || "0").toString()) || 0;
    },
    _getDiscountableBaseAmount() {
        return Math.max(Math.abs((this.get_unit_price() || 0) * (this.get_quantity() || 0)), 0);
    },
    _syncAmountDiscountToPercentage() {
        if (this.getDiscountType() !== "amount") {
            return;
        }
        const baseAmount = this._getDiscountableBaseAmount();
        const safeAmount = Math.max(this.getDiscountAmount() || 0, 0);
        const cappedAmount = Math.min(safeAmount, baseAmount);
        const percentage = baseAmount ? (cappedAmount / baseAmount) * 100 : 0;

        this.discount_amount = cappedAmount;
        super.set_discount(percentage);
    },
});

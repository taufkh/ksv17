/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { floatIsZero } from "@web/core/utils/numbers";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { Order } from "@point_of_sale/app/store/models";

function isZeroAmount(order, amount) {
    return floatIsZero(amount || 0, order.pos.currency.decimal_places);
}

patch(Order.prototype, {
    getNonZeroPaymentLines() {
        return this.get_paymentlines().filter((line) => !isZeroAmount(this, line.amount));
    },

    removeZeroAmountPaymentLines() {
        for (const line of [...this.get_paymentlines()]) {
            if (isZeroAmount(this, line.amount)) {
                this.remove_paymentline(line);
            }
        }
    },

    add_paymentline(paymentMethod) {
        this.removeZeroAmountPaymentLines();

        const nonZeroLines = this.getNonZeroPaymentLines();
        const due = this.get_due ? this.get_due() : 0;
        const fullyPaid = floatIsZero(due, this.pos.currency.decimal_places);

        if (nonZeroLines.length && fullyPaid) {
            this.pos.popup.add(ErrorPopup, {
                title: _t("Payment Method sudah dipilih"),
                body: _t(
                    "Transaksi ini sudah lunas dengan payment method yang dipilih. Untuk split payment, input nominal parsial pada payment method pertama terlebih dahulu."
                ),
            });
            return false;
        }

        return super.add_paymentline(...arguments);
    },
});

patch(PaymentScreen.prototype, {
    async _isOrderValid(isForceValidate) {
        this.currentOrder.removeZeroAmountPaymentLines();
        return await super._isOrderValid(...arguments);
    },
});

/** @odoo-module */

import { BrownielabPaymentReminderPopup } from "../../popups/payment_reminder_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async afterOrderValidation(suggestToSync = true) {
        this.pos.db.remove_unpaid_order(this.currentOrder);

        if (suggestToSync && this.pos.db.get_orders().length) {
            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Remaining unsynced orders"),
                body: _t("There are unsynced orders. Do you want to sync these orders?"),
            });
            if (confirmed) {
                this.pos.push_orders();
            }
        }

        let nextScreen = this.nextScreen;

        if (
            nextScreen === "ReceiptScreen" &&
            !this.currentOrder._printed &&
            this.pos.config.iface_print_auto
        ) {
            const invoicedFinalized = this.currentOrder.is_to_invoice()
                ? this.currentOrder.finalized
                : true;

            if (invoicedFinalized) {
                const printResult = await this.printer.print(
                    OrderReceipt,
                    {
                        data: this.pos.get_order().export_for_printing(),
                        formatCurrency: this.env.utils.formatCurrency,
                    },
                    { webPrintFallback: true }
                );

                if (printResult && this.pos.config.iface_print_skip_screen) {
                    await this._showBrownielabPaymentReminderFromPaymentScreen();
                    this.pos.removeOrder(this.currentOrder);
                    this.pos.add_new_order();
                    nextScreen = "ProductScreen";
                }
            }
        }

        this.pos.showScreen(nextScreen);
    },

    async _showBrownielabPaymentReminderFromPaymentScreen() {
        if (!this._shouldShowBrownielabPaymentReminderFromPaymentScreen()) {
            return;
        }

        this.currentOrder._brownielabPaymentReminderShown = true;
        const message = this.pos.config.brownielab_payment_reminder_message.trim();

        await this.popup.add(BrownielabPaymentReminderPopup, {
            title: "Reminder",
            confirmText: "OK",
            lines: message.split("\n").map((line) => line.trim()).filter(Boolean),
            styleConfig: this._getBrownielabReminderStyleConfig(),
        });
    },

    _shouldShowBrownielabPaymentReminderFromPaymentScreen() {
        const message = this.pos.config?.brownielab_payment_reminder_message;
        return Boolean(
            this.pos.config?.brownielab_payment_reminder_enabled &&
                this.currentOrder &&
                !this.currentOrder._brownielabPaymentReminderShown &&
                typeof message === "string" &&
                message.trim()
        );
    },

    _getBrownielabReminderStyleConfig() {
        const config = this.pos.config || {};
        const toInt = (value, fallback, minimum) => {
            const parsed = Number(value || fallback);
            return Number.isFinite(parsed) && parsed >= minimum ? parsed : fallback;
        };
        return {
            bodyFontSize: toInt(config.brownielab_payment_reminder_font_size, 30, 16),
            titleFontSize: toInt(config.brownielab_payment_reminder_title_font_size, 38, 18),
            buttonFontSize: toInt(config.brownielab_payment_reminder_button_font_size, 28, 16),
            fontFamily: config.brownielab_payment_reminder_font_family || "inherit",
            titleBold: config.brownielab_payment_reminder_title_bold !== false,
            bodyBold: config.brownielab_payment_reminder_body_bold !== false,
            buttonBold: config.brownielab_payment_reminder_button_bold !== false,
            titleItalic: Boolean(config.brownielab_payment_reminder_title_italic),
            bodyItalic: Boolean(config.brownielab_payment_reminder_body_italic),
            buttonItalic: Boolean(config.brownielab_payment_reminder_button_italic),
            titleUnderline: Boolean(config.brownielab_payment_reminder_title_underline),
            bodyUnderline: Boolean(config.brownielab_payment_reminder_body_underline),
            buttonUnderline: Boolean(config.brownielab_payment_reminder_button_underline),
            titleAlign: config.brownielab_payment_reminder_title_align || "center",
            bodyAlign: config.brownielab_payment_reminder_body_align || "left",
            textColor: config.brownielab_payment_reminder_text_color || "#1f2937",
            buttonBackground:
                config.brownielab_payment_reminder_button_background || "#7a4d72",
            buttonTextColor:
                config.brownielab_payment_reminder_button_text_color || "#ffffff",
        };
    },
});

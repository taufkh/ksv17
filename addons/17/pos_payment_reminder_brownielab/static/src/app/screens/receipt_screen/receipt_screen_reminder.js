/** @odoo-module */

import { onMounted } from "@odoo/owl";
import { BrownielabPaymentReminderPopup } from "@pos_payment_reminder_brownielab/app/popups/payment_reminder_popup";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";

patch(ReceiptScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");

        onMounted(async () => {
            await this._showBrownielabPaymentReminder();
        });
    },

    async _showBrownielabPaymentReminder() {
        if (!this._shouldShowBrownielabPaymentReminder()) {
            return;
        }

        this.currentOrder._brownielabPaymentReminderShown = true;
        const message = this.pos.config.brownielab_payment_reminder_message.trim();

        const { confirmed } = await this.popup.add(BrownielabPaymentReminderPopup, {
            title: "Reminder",
            confirmText: "OK",
            lines: message.split("\n").map((line) => line.trim()).filter(Boolean),
            styleConfig: this._getBrownielabReminderStyleConfig(),
        });

        if (confirmed) {
            await this.orderDone();
        }
    },

    _shouldShowBrownielabPaymentReminder() {
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

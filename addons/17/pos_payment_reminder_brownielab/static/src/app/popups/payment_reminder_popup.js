/** @odoo-module */

import { AbstractAwaitablePopup } from "@point_of_sale/app/popup/abstract_awaitable_popup";

export class BrownielabPaymentReminderPopup extends AbstractAwaitablePopup {
    static template = "pos_payment_reminder_brownielab.PaymentReminderPopup";
    static defaultProps = {
        title: "Reminder",
        confirmText: "OK",
        lines: [],
        styleConfig: {},
    };

    _formatStyle(styleMap) {
        return Object.entries(styleMap)
            .filter(([, value]) => value !== undefined && value !== null && value !== "")
            .map(([key, value]) => `${key}: ${value}`)
            .join("; ");
    }

    _fontWeight(enabled) {
        return enabled ? "800" : "400";
    }

    _fontStyle(enabled) {
        return enabled ? "italic" : "normal";
    }

    _textDecoration(enabled) {
        return enabled ? "underline" : "none";
    }

    get titleStyle() {
        const config = this.props.styleConfig;
        return this._formatStyle({
            "font-size": `${config.titleFontSize}px`,
            "font-family": config.fontFamily,
            "font-weight": this._fontWeight(config.titleBold),
            "font-style": this._fontStyle(config.titleItalic),
            "text-decoration": this._textDecoration(config.titleUnderline),
            color: config.textColor,
            "text-align": config.titleAlign,
        });
    }

    get bodyStyle() {
        const config = this.props.styleConfig;
        return this._formatStyle({
            "font-size": `${config.bodyFontSize}px`,
            "font-family": config.fontFamily,
            "text-align": config.bodyAlign,
            color: config.textColor,
        });
    }

    get lineStyle() {
        const config = this.props.styleConfig;
        return this._formatStyle({
            "font-weight": this._fontWeight(config.bodyBold),
            "font-style": this._fontStyle(config.bodyItalic),
            "text-decoration": this._textDecoration(config.bodyUnderline),
        });
    }

    get buttonStyle() {
        const config = this.props.styleConfig;
        return this._formatStyle({
            "font-size": `${config.buttonFontSize}px`,
            "font-family": config.fontFamily,
            "font-weight": this._fontWeight(config.buttonBold),
            "font-style": this._fontStyle(config.buttonItalic),
            "text-decoration": this._textDecoration(config.buttonUnderline),
            background: config.buttonBackground,
            "border-color": config.buttonBackground,
            color: config.buttonTextColor,
        });
    }
}

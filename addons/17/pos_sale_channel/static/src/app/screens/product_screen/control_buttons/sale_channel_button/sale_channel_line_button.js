/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

export class SaleChannelLineButton extends Component {
    static template = "pos_sale_channel.SaleChannelLineButton";
    static props = {};

    setup() {
        this.pos = usePos();
    }

    get order() {
        return this.pos.get_order();
    }

    get selectedLine() {
        return this.order?.get_selected_orderline();
    }

    get label() {
        if (!this.selectedLine) {
            return _t("Item Channel");
        }
        if (!this.selectedLine.hasSaleChannelOverride()) {
            return _t("Item: Follow Order");
        }
        return _t("Item: %s", this.selectedLine.getSaleChannelName());
    }

    async onClick() {
        const line = this.selectedLine;
        if (!line) {
            return;
        }

        const order = this.order;
        const followOrderId = `follow-order-${order.uid}`;
        const options = [
            {
                id: followOrderId,
                label: _t("Follow Order Channel (%s)", order.getSaleChannelName()),
                item: false,
                isSelected: !line.hasSaleChannelOverride(),
            },
            ...(this.pos.sale_channels || []).map((channel) => ({
                id: channel.id,
                label: channel.name,
                item: channel.id,
                isSelected: line.hasSaleChannelOverride() && channel.id === line.sale_channel_id,
            })),
        ];

        const { confirmed, payload } = await this.pos.popup.add(SelectionPopup, {
            title: _t("Item Sales Channel"),
            list: options,
        });
        if (!confirmed) {
            return;
        }
        line.setSaleChannelId(payload || false);
    }
}

ProductScreen.addControlButton({
    component: SaleChannelLineButton,
    position: ["before", "SaleChannelButton"],
    condition: function () {
        const order = this.pos.get_order();
        const selectedLine = order?.get_selected_orderline();
        return !!(order && selectedLine && (this.pos.sale_channels || []).length);
    },
});

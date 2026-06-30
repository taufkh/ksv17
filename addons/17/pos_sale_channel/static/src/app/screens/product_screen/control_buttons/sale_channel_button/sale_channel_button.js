/** @odoo-module */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { SelectionPopup } from "@point_of_sale/app/utils/input_popups/selection_popup";

export class SaleChannelButton extends Component {
    static template = "pos_sale_channel.SaleChannelButton";
    static props = {};

    setup() {
        this.pos = usePos();
    }

    get currentChannelLabel() {
        const order = this.pos.get_order();
        return order ? _t("Order: %s", order.getSaleChannelName()) : _t("Order Channel");
    }

    async onClick() {
        const channels = this.pos.sale_channels || [];
        const order = this.pos.get_order();
        if (!order || !channels.length) {
            return;
        }

        const { confirmed, payload } = await this.pos.popup.add(SelectionPopup, {
            title: _t("Sales Channel"),
            list: channels.map((channel) => ({
                id: channel.id,
                label: channel.name,
                item: channel.id,
                isSelected: channel.id === order.getSaleChannelId(),
            })),
        });

        if (confirmed && payload) {
            order.setSaleChannelId(payload);
        }
    }
}

ProductScreen.addControlButton({
    component: SaleChannelButton,
    position: ["before", "CustomerButton"],
    condition: function () {
        return (this.pos.sale_channels || []).length > 0;
    },
});

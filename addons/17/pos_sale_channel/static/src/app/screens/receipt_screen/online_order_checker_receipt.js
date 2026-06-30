/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";
import { _t } from "@web/core/l10n/translation";

patch(ReceiptScreen.prototype, {
    getOnlineCheckerOrderId() {
        if (!this.currentOrder) {
            return false;
        }
        const orderName = this.currentOrder.get_name?.();
        const serverId =
            this.currentOrder.server_id ||
            this.pos.validated_orders_name_server_id_map?.[orderName] ||
            false;
        if (serverId) {
            this.currentOrder.server_id = serverId;
        }
        return serverId;
    },
    shouldShowOnlineCheckerButton() {
        const order = this.currentOrder;
        if (!order) {
            return false;
        }
        const channelId = order.getSaleChannelId?.();
        return !!(this.pos.isOnlineCheckerChannelId?.(channelId) && this.getOnlineCheckerOrderId());
    },
    getOnlineCheckerReceiptButtonLabel() {
        if (!this.currentOrder) {
            return _t("Start Checker");
        }
        return ["checked", "overridden"].includes(this.currentOrder.getOnlineCheckStatus())
            ? _t("Open Checker")
            : _t("Start Checker");
    },
    openOnlineOrderChecker() {
        const orderId = this.getOnlineCheckerOrderId();
        if (!orderId) {
            return;
        }
        this.pos.showScreen("OnlineOrderCheckerScreen", {
            orderId,
            returnScreen: "ReceiptScreen",
            orderProxy: this.currentOrder,
        });
    },
});

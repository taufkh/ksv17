/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {
    selectedOrderCanUseOnlineChecker() {
        const order = this.getSelectedOrder?.();
        return !!(order && order.backendId && order.online_check_required);
    },
    getSelectedOrderOnlineCheckerLabel() {
        const order = this.getSelectedOrder?.();
        if (!order) {
            return _t("Open Checker");
        }
        return ["checked", "overridden"].includes(order.online_check_status) ? _t("Open Checker") : _t("Start Checker");
    },
    openSelectedOrderOnlineChecker() {
        const order = this.getSelectedOrder?.();
        if (!order?.backendId) {
            return;
        }
        this.pos.showScreen("OnlineOrderCheckerScreen", {
            orderId: order.backendId,
            returnScreen: "TicketScreen",
            orderProxy: order,
        });
    },
});

/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

patch(PosStore.prototype, {
    canManageOnlineChecker() {
        return !!this.config?.online_checker_can_manage;
    },
    isOnlineCheckerChannelId(channelId) {
        return !!channelId && (this.config?.online_checker_channel_ids || []).includes(channelId);
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.online_check_required = !!this.online_check_required;
        this.online_check_status = this.online_check_status || "not_required";
        this.online_check_note = this.online_check_note || "";
        this.online_check_progress_display = this.online_check_progress_display || "";
        this.online_check_can_manage = this.online_check_can_manage ?? this.pos.canManageOnlineChecker();
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.online_check_required = !!json.online_check_required;
        this.online_check_status = json.online_check_status || "not_required";
        this.online_check_note = json.online_check_note || "";
        this.online_check_progress_display = json.online_check_progress_display || "";
        this.online_check_can_manage = json.online_check_can_manage ?? this.pos.canManageOnlineChecker();
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.online_check_required = !!this.online_check_required;
        json.online_check_status = this.online_check_status || "not_required";
        json.online_check_note = this.online_check_note || "";
        json.online_check_progress_display = this.online_check_progress_display || "";
        return json;
    },
    setOnlineCheckerReceiptData(data) {
        if (!data) {
            return;
        }
        this.online_check_required = !!data.online_check_required;
        this.online_check_status = data.online_check_status || "not_required";
        this.online_check_note = data.online_check_note || "";
        this.online_check_progress_display = data.online_check_progress_display || "";
        this.online_check_can_manage = data.online_check_can_manage ?? this.pos.canManageOnlineChecker();
        if (data.order_id) {
            this.server_id = data.order_id;
        }
    },
    requiresOnlineChecker() {
        return !!this.online_check_required;
    },
    canManageOnlineChecker() {
        return this.online_check_can_manage ?? this.pos.canManageOnlineChecker();
    },
    getOnlineCheckStatus() {
        return this.online_check_status || "not_required";
    },
    getOnlineCheckButtonLabel() {
        return ["checked", "overridden"].includes(this.getOnlineCheckStatus()) ? "Open Checker" : "Start Checker";
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.online_check_qty = this.online_check_qty || 0;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.online_check_qty = json.online_check_qty || 0;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.online_check_qty = this.online_check_qty || 0;
        return json;
    },
});

patch(PaymentScreen.prototype, {
    async _postPushOrderResolve(order, order_server_ids) {
        const result = await super._postPushOrderResolve(...arguments);
        const serverIds = (order_server_ids || [])
            .map((item) => (typeof item === "object" ? item.id : item))
            .filter(Boolean);
        if (!serverIds.length) {
            return result;
        }

        order.server_id = serverIds[0];
        const checkerData = await this.orm.call("pos.order", "read_online_checker_receipt_data", [serverIds]);
        if (checkerData?.[0]) {
            order.setOnlineCheckerReceiptData(checkerData[0]);
        }
        return result;
    },
});

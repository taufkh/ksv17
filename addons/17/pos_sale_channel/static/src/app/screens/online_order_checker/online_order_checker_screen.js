/** @odoo-module */

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { TextAreaPopup } from "@point_of_sale/app/utils/input_popups/textarea_popup";

export class OnlineOrderCheckerScreen extends Component {
    static template = "pos_sale_channel.OnlineOrderCheckerScreen";
    static props = ["orderId?", "order?", "orderProxy?", "returnScreen?"];

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.popup = useService("popup");
        this.notification = useService("pos_notification");
        this.state = useState({
            isLoading: true,
            orderId: false,
            orderName: "",
            saleChannelName: "",
            partnerName: "",
            onlineCheckRequired: false,
            onlineCheckStatus: "not_required",
            onlineCheckNote: "",
            onlineCheckCanManage: false,
            onlineCheckOverrideReason: "",
            lines: [],
        });

        onWillStart(async () => {
            await this.reload();
        });
    }

    get orderId() {
        return this.props.orderId || this.props.order?.backendId || this.props.orderProxy?.server_id;
    }

    get returnScreen() {
        return this.props.returnScreen || "ProductScreen";
    }

    get statusBadgeClass() {
        return {
            not_required: "bg-secondary",
            pending: "bg-warning text-dark",
            in_progress: "bg-info text-dark",
            checked: "bg-success",
            overridden: "bg-danger",
        }[this.state.onlineCheckStatus];
    }

    get canEdit() {
        return this.state.onlineCheckRequired && !["checked", "overridden"].includes(this.state.onlineCheckStatus);
    }

    get currentOrderedQtyTotal() {
        return this.state.lines.reduce((sum, line) => sum + Number(line.ordered_qty || 0), 0);
    }

    get currentCheckedQtyTotal() {
        return this.state.lines.reduce((sum, line) => sum + Number(line.checked_qty || 0), 0);
    }

    get currentTotalLineCount() {
        return this.state.lines.length;
    }

    get currentCheckedLineCount() {
        return this.state.lines.filter((line) => Number(line.checked_qty || 0) >= Number(line.ordered_qty || 0)).length;
    }

    get currentProgressDisplay() {
        return `${this.formatQty(this.currentCheckedQtyTotal)}/${this.formatQty(this.currentOrderedQtyTotal)} qty | ${this.currentCheckedLineCount}/${this.currentTotalLineCount} lines`;
    }

    get isFullyMatched() {
        return (
            this.currentTotalLineCount > 0 &&
            this.state.lines.every((line) => Number(line.checked_qty || 0) >= Number(line.ordered_qty || 0))
        );
    }

    formatQty(qty) {
        const rounded = Math.round((Number(qty || 0) + Number.EPSILON) * 100) / 100;
        if (Math.abs(rounded - Math.trunc(rounded)) < 0.000001) {
            return `${Math.trunc(rounded)}`;
        }
        return `${rounded}`;
    }

    async reload() {
        if (!this.orderId) {
            this.state.isLoading = false;
            return;
        }
        const payload = await this.orm.call("pos.order", "get_online_checker_payload", [[this.orderId]]);
        this.applyPayload(payload);
    }

    applyPayload(payload) {
        this.state.orderId = payload.order_id;
        this.state.orderName = payload.order_name || "";
        this.state.saleChannelName = payload.sale_channel_name || "";
        this.state.partnerName = payload.partner_name || "";
        this.state.onlineCheckRequired = !!payload.online_check_required;
        this.state.onlineCheckStatus = payload.online_check_status || "not_required";
        this.state.onlineCheckNote = payload.online_check_note || "";
        this.state.onlineCheckCanManage = !!payload.online_check_can_manage;
        this.state.onlineCheckOverrideReason = payload.online_check_override_reason || "";
        this.state.lines = (payload.lines || []).map((line) => ({ ...line }));
        this.state.isLoading = false;

        if (this.props.orderProxy) {
            if (typeof this.props.orderProxy.setOnlineCheckerReceiptData === "function") {
                this.props.orderProxy.setOnlineCheckerReceiptData(payload);
            } else {
                this.props.orderProxy.online_check_required = !!payload.online_check_required;
                this.props.orderProxy.online_check_status = payload.online_check_status || "not_required";
                this.props.orderProxy.online_check_note = payload.online_check_note || "";
                this.props.orderProxy.online_check_progress_display = payload.online_check_progress_display || "";
            }
        }
    }

    back() {
        const returnScreen = this.returnScreen;
        for (const order of [this.props.orderProxy, this.pos.get_order?.()]) {
            if (!order?.set_screen_data) {
                continue;
            }
            const currentScreenData = order.get_screen_data?.() || {};
            order.set_screen_data({
                ...currentScreenData,
                name: returnScreen,
            });
        }
        this.pos.showScreen(returnScreen);
    }

    onNoteInput(ev) {
        this.state.onlineCheckNote = ev.target.value;
    }

    getLineById(lineId) {
        return this.state.lines.find((line) => line.line_id === lineId);
    }

    getLineIdFromEvent(ev) {
        return Number(ev.currentTarget.dataset.lineId || 0);
    }

    setCheckedQty(lineId, checkedQty) {
        if (!this.canEdit) {
            return;
        }
        this.state.lines = this.state.lines.map((line) => {
            if (line.line_id !== lineId) {
                return line;
            }
            const clampedQty = Math.min(Math.max(Number(checkedQty || 0), 0), Number(line.ordered_qty || 0));
            return {
                ...line,
                checked_qty: clampedQty,
                remaining_qty: Math.max(Number(line.ordered_qty || 0) - clampedQty, 0),
                status:
                    clampedQty <= 0
                        ? "unchecked"
                        : clampedQty >= Number(line.ordered_qty || 0)
                          ? "full"
                          : "partial",
            };
        });
    }

    incrementLine(line) {
        if (!line) {
            return;
        }
        this.setCheckedQty(line.line_id, Number(line.checked_qty || 0) + 1);
    }

    setLineFull(line) {
        if (!line) {
            return;
        }
        this.setCheckedQty(line.line_id, Number(line.ordered_qty || 0));
    }

    resetLine(line) {
        if (!line) {
            return;
        }
        this.setCheckedQty(line.line_id, 0);
    }

    onIncrementLine(ev) {
        this.incrementLine(this.getLineById(this.getLineIdFromEvent(ev)));
    }

    onSetLineFull(ev) {
        this.setLineFull(this.getLineById(this.getLineIdFromEvent(ev)));
    }

    onResetLine(ev) {
        this.resetLine(this.getLineById(this.getLineIdFromEvent(ev)));
    }

    buildPayload() {
        return {
            note: this.state.onlineCheckNote || "",
            line_updates: this.state.lines.map((line) => ({
                line_id: line.line_id,
                checked_qty: Number(line.checked_qty || 0),
            })),
        };
    }

    async saveProgress() {
        const payload = await this.orm.call("pos.order", "save_online_checker_progress", [[this.state.orderId], this.buildPayload()]);
        this.applyPayload(payload);
        this.notification.add(_t("Online checker progress saved."));
    }

    async completeChecker() {
        const payload = await this.orm.call("pos.order", "complete_online_checker", [[this.state.orderId], this.buildPayload()]);
        this.applyPayload(payload);
        this.notification.add(_t("Online checker completed."));
    }

    async overrideChecker() {
        const { confirmed, payload: reason } = await this.popup.add(TextAreaPopup, {
            title: _t("Override Reason"),
            startingValue: this.state.onlineCheckOverrideReason || "",
        });
        if (!confirmed) {
            return;
        }
        const payload = await this.orm.call("pos.order", "override_online_checker", [
            [this.state.orderId],
            reason || "",
            this.buildPayload(),
        ]);
        this.applyPayload(payload);
        this.notification.add(_t("Online checker overridden."));
    }

    async reopenChecker() {
        const payload = await this.orm.call("pos.order", "reopen_online_checker", [[this.state.orderId]]);
        this.applyPayload(payload);
        this.notification.add(_t("Online checker reopened."));
    }
}

registry.category("pos_screens").add("OnlineOrderCheckerScreen", OnlineOrderCheckerScreen);

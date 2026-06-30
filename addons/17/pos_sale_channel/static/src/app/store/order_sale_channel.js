/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async _processData(loadedData) {
        await super._processData(...arguments);
        this.sale_channels = loadedData["pos.sale.channel"] || [];
    },
    getDefaultSaleChannelId() {
        return this.sale_channels?.length ? this.sale_channels[0].id : false;
    },
    getSaleChannelById(channelId) {
        return (this.sale_channels || []).find((channel) => channel.id === channelId);
    },
    getSaleChannelByType(channelType) {
        return (this.sale_channels || []).find((channel) => channel.channel_type === channelType);
    },
    getDineInChannel() {
        return (
            this.getSaleChannelByType("dine_in") ||
            (this.sale_channels || []).find((channel) => channel.name?.toLowerCase() === "dine in")
        );
    },
    getTakeawayChannel() {
        return (
            this.getSaleChannelByType("takeaway") ||
            (this.sale_channels || []).find((channel) => channel.name?.toLowerCase() === "takeaway")
        );
    },
});

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.sale_channel_id = this.sale_channel_id || this.pos.getDefaultSaleChannelId();
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.sale_channel_id = json.sale_channel_id || this.pos.getDefaultSaleChannelId();
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.sale_channel_id = this.getSaleChannelId();
        return json;
    },
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.sale_channel = this.getSaleChannelName();
        result.headerData = {
            ...(result.headerData || {}),
            sale_channel: this.getSaleChannelName(),
        };
        return result;
    },
    setSaleChannelId(channelId) {
        this.assert_editable();
        this.sale_channel_id = channelId;
        for (const line of this.get_orderlines()) {
            line.sale_channel_id = channelId;
        }
        this.save_to_db();
    },
    getSaleChannelId() {
        return this.sale_channel_id || this.pos.getDefaultSaleChannelId();
    },
    getSaleChannel() {
        return (this.pos.sale_channels || []).find((channel) => channel.id === this.getSaleChannelId());
    },
    getSaleChannelName() {
        return this.getSaleChannel()?.name || _t("Unassigned");
    },
    getSaleChannelType() {
        const channel = this.getSaleChannel();
        const channelType = channel?.channel_type || "other";
        if (channelType !== "other") {
            return channelType;
        }
        const normalizedName = (channel?.name || "").toLowerCase();
        if (normalizedName === "dine in") {
            return "dine_in";
        }
        if (normalizedName === "takeaway") {
            return "takeaway";
        }
        return "other";
    },
    isDineInTakeawayOrder() {
        const type = this.getSaleChannelType();
        return type === "dine_in" || type === "takeaway";
    },
});

patch(Orderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.sale_channel_id = this.sale_channel_id || false;
    },
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.sale_channel_id = json.sale_channel_id || false;
    },
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.sale_channel_id = this.sale_channel_id || false;
        return json;
    },
    setSaleChannelId(channelId) {
        this.order.assert_editable();
        this.sale_channel_id = channelId;
        this.order.save_to_db();
    },
    getSaleChannelId() {
        return this.sale_channel_id || this.order?.getSaleChannelId() || false;
    },
    hasSaleChannelOverride() {
        return !!this.sale_channel_id;
    },
    getSaleChannel() {
        return this.order?.pos.getSaleChannelById(this.getSaleChannelId());
    },
    getSaleChannelName() {
        return this.getSaleChannel()?.name || this.order?.getSaleChannelName() || _t("Unassigned");
    },
    isTakeawayLine() {
        const channel = this.getSaleChannel();
        return channel?.channel_type === "takeaway" || (channel?.name || "").toLowerCase() === "takeaway";
    },
});

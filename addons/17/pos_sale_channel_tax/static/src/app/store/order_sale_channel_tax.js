/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    getTaxById(taxId) {
        return this.taxes_by_id?.[taxId] || null;
    },

    getSaleChannelTaxIds(channelId) {
        const channel = this.getSaleChannelById ? this.getSaleChannelById(channelId) : null;
        const taxId = Array.isArray(channel?.channel_tax_id)
            ? channel.channel_tax_id[0]
            : channel?.channel_tax_id;

        return this.getTaxById(taxId) ? [taxId] : undefined;
    },
});

patch(Order.prototype, {
    getSaleChannelMappedTaxIds(channelId = null) {
        return this.pos.getSaleChannelTaxIds(channelId || this.getSaleChannelId());
    },

    _applySaleChannelTaxes(channelId = null) {
        const taxIds = this.getSaleChannelMappedTaxIds(channelId);
        for (const line of this.get_orderlines()) {
            line.tax_ids = taxIds;
        }
    },

    setSaleChannelId(channelId) {
        super.setSaleChannelId(...arguments);
        this._applySaleChannelTaxes(channelId);
        this.save_to_db();
    },

    set_orderline_options(orderline, options) {
        if (options.tax_ids === undefined) {
            options.tax_ids = this.getSaleChannelMappedTaxIds();
        }
        super.set_orderline_options(...arguments);
    },
});
